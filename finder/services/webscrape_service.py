from bs4 import BeautifulSoup
import requests
import re
import logging
from urllib.parse import urljoin, urlparse
import time
import random
from collections import deque
import threading
from concurrent.futures import ThreadPoolExecutor
import tldextract
from contacts.models import Contact

logger = logging.getLogger(__name__)

class WebScrapeService:
    """
    Service to scrape websites for contact information, particularly email addresses.
    """
    
    # Common webmail domains to filter out
    COMMON_WEBMAIL_DOMAINS = {
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 
        'icloud.com', 'protonmail.com', 'mail.com', 'zoho.com', 'yandex.com',
        'live.com', 'msn.com', 'me.com', 'gmx.com', 'inbox.com'
    }
    
    def __init__(self, config):
        """
        Initialize the web scraper with configuration.
        
        Args:
            config (dict): Configuration for the scraper
        """
        self.target_url = config.get('target_url')
        self.max_depth = config.get('max_depth', 2)
        self.max_pages = config.get('max_pages', 100)
        self.stay_within_domain = config.get('stay_within_domain', True)
        self.follow_subdomains = config.get('follow_subdomains', True)
        self.priority_paths = config.get('priority_paths', [])
        self.exclude_paths = config.get('exclude_paths', [])
        self.target_keywords = config.get('target_keywords', [])
        self.extract_names = config.get('extract_names', True)
        self.extract_job_titles = config.get('extract_job_titles', True)
        self.extract_phone_numbers = config.get('extract_phone_numbers', True)
        self.request_delay = config.get('request_delay', 1.0)
        self.concurrent_requests = config.get('concurrent_requests', 5)
        self.request_timeout = config.get('request_timeout', 30.0)
        self.follow_robotstxt = config.get('follow_robotstxt', True)
        self.user_agent = config.get('user_agent', "Mozilla/5.0 (compatible; CompanyBot/1.0)")
        
        # Extract base domain for filtering
        self.base_domain = self._extract_base_domain(self.target_url)
        
        # Set up threading primitives
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        
        # Initialize results and tracking sets
        self.results = {
            'emails': {},  # Will store emails mapped to page details
            'phones': set(),
        }
        self.visited_urls = set()
        self.queued_urls = set()
        self.url_queue = deque()
        
        # Compile regex patterns
        self.email_pattern = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
        self.phone_pattern = re.compile(r'(\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}')
        self.name_pattern = re.compile(r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)')  # Simple name pattern
        self.title_pattern = re.compile(
            r'\b(CEO|CTO|CFO|COO|Director|Manager|President|VP|Vice President|Chief|Officer|Founder|Co-founder|Lead|Head|Principal)\b',
            re.IGNORECASE
        )
        
    def _extract_base_domain(self, url):
        """Extract the base domain for comparison."""
        extracted = tldextract.extract(url)
        return f"{extracted.domain}.{extracted.suffix}"
    
    def start(self):
        """Start the scraping process."""
        logger.info(f"Starting web scrape of {self.target_url}")
        
        # Add initial URL to queue
        self._add_url_to_queue(self.target_url, depth=0)
        
        # If we have priority paths, add them first
        if self.priority_paths:
            base_url = self.target_url.rstrip('/')
            for path in self.priority_paths:
                path = path.lstrip('/')
                priority_url = f"{base_url}/{path}"
                self._add_url_to_queue(priority_url, depth=0, priority=True)
        
        # Process queue using thread pool
        with ThreadPoolExecutor(max_workers=self.concurrent_requests) as executor:
            futures = set()
            
            while (self.url_queue or futures) and not self._stop_event.is_set():
                # Fill worker pool
                while self.url_queue and len(futures) < self.concurrent_requests:
                    try:
                        url, depth, priority = self.url_queue.popleft()
                        futures.add(executor.submit(self._process_url, url, depth))
                    except IndexError:
                        break  # Queue emptied by another thread
                
                # Wait for at least one worker to complete
                done, futures = wait_for_any(futures)
                
                # Check results of completed futures
                for future in done:
                    try:
                        future.result()  # Get result to catch exceptions
                    except Exception as e:
                        logger.error(f"Error processing URL: {str(e)}")
                
                # Check if we've reached the max pages limit
                if len(self.visited_urls) >= self.max_pages:
                    logger.info(f"Reached maximum pages limit: {self.max_pages}")
                    break
        
        logger.info(f"Web scrape completed. Visited {len(self.visited_urls)} pages.")
        logger.info(f"Found {len(self.results['emails'])} email addresses and {len(self.results['phones'])} phone numbers.")
        
        return self.results
    
    def stop(self):
        """Stop the scraping process."""
        self._stop_event.set()
    
    def _add_url_to_queue(self, url, depth=0, priority=False):
        """Add a URL to the processing queue if it hasn't been visited or queued."""
        # Normalize URL
        url = url.split('#')[0]  # Remove fragment
        url = url.rstrip('/')  # Standardize trailing slash
        
        with self._lock:
            if url in self.visited_urls or url in self.queued_urls:
                return False
            
            # Check if within domain constraint
            if self.stay_within_domain:
                parsed_url = urlparse(url)
                if not parsed_url.netloc:  # Handle relative URLs
                    return False
                
                # Check domain matching
                url_domain = self._extract_base_domain(url)
                if url_domain != self.base_domain:
                    # If following subdomains, check if subdomain of base
                    if not (self.follow_subdomains and url_domain.endswith(f".{self.base_domain}")):
                        return False
            
            # Check if path is excluded
            for exclude_path in self.exclude_paths:
                if exclude_path in url:
                    return False
            
            # Add to queue
            self.queued_urls.add(url)
            if priority:
                self.url_queue.appendleft((url, depth, priority))
            else:
                self.url_queue.append((url, depth, priority))
            
            return True
    
    def _process_url(self, url, depth):
        """Process a single URL: fetch, extract data, find new links."""
        if self._stop_event.is_set() or len(self.visited_urls) >= self.max_pages:
            return
        
        logger.debug(f"Processing {url} (depth {depth})")
        
        try:
            # Mark as visited early to prevent duplicates
            with self._lock:
                self.visited_urls.add(url)
                self.queued_urls.discard(url)
            
            # Random delay to be polite
            if self.request_delay > 0:
                time.sleep(self.request_delay * (0.5 + random.random()))
            
            # Make the request
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers, timeout=self.request_timeout)
            
            # Skip non-HTML responses
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type:
                return
            
            # Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract contact information
            self._extract_contact_info(url, soup)
            
            # Follow links if we haven't reached max depth
            if depth < self.max_depth:
                self._extract_links(url, soup, depth + 1)
                
        except requests.RequestException as e:
            logger.warning(f"Request failed for {url}: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
    
    def _extract_contact_info(self, url, soup):
        """Extract contact information from the page."""
        # Look for emails in the page content
        content_text = soup.get_text()
        page_emails = set(self.email_pattern.findall(content_text))
        
        # Filter out webmail addresses
        business_emails = self._filter_business_emails(page_emails)
        
        # Check if any emails found
        if not business_emails:
            return
        
        # Extract the page title and relevant page text
        page_title = soup.title.string if soup.title else "No Title"
        
        # Store emails with associated page details
        with self._lock:
            for email in business_emails:
                if email not in self.results['emails']:
                    email_data = {
                        'email': email,
                        'source_url': url,
                        'page_title': page_title,
                    }
                    
                    # Try to find name and title near the email
                    if self.extract_names or self.extract_job_titles:
                        # Get context around email by finding elements containing the email
                        for element in soup.find_all(string=re.compile(re.escape(email))):
                            parent_text = element.parent.get_text()
                            
                            # Extract name if enabled
                            if self.extract_names:
                                name_match = self._extract_name_near_email(parent_text, email)
                                if name_match:
                                    email_data['name'] = name_match
                            
                            # Extract title if enabled
                            if self.extract_job_titles:
                                title_match = self._extract_title_near_email(parent_text, email)
                                if title_match:
                                    email_data['title'] = title_match
                    
                    # Store the data
                    self.results['emails'][email] = email_data
        
        # Extract phone numbers if enabled
        if self.extract_phone_numbers:
            phone_numbers = set(self.phone_pattern.findall(content_text))
            with self._lock:
                self.results['phones'].update(phone_numbers)
    
    def _filter_business_emails(self, emails):
        """Filter out common webmail addresses to focus on business emails."""
        business_emails = set()
        
        for email in emails:
            try:
                username, domain = email.split('@')
                if domain.lower() not in self.COMMON_WEBMAIL_DOMAINS:
                    business_emails.add(email)
            except ValueError:
                # Skip invalid emails
                pass
        
        return business_emails
    
    def _extract_name_near_email(self, text, email):
        """Try to extract a name near the email address."""
        # First, try to get the name from the email prefix
        username = email.split('@')[0]
        if '.' in username:
            name_parts = username.split('.')
            if len(name_parts) == 2:
                # Convert to title case for names
                first_name = name_parts[0].title()
                last_name = name_parts[1].title()
                if len(first_name) > 1 and len(last_name) > 1:  # Avoid single letters
                    return f"{first_name} {last_name}"
        
        # Next, look for names in the text near the email
        email_position = text.find(email)
        if email_position >= 0:
            # Check a reasonable context before and after the email
            context_start = max(0, email_position - 100)
            context_end = min(len(text), email_position + 100)
            context = text[context_start:context_end]
            
            # Look for name patterns
            names = self.name_pattern.findall(context)
            
            # Return the first name that looks reasonable
            for name in names:
                parts = name.split()
                if len(parts) >= 2 and all(len(part) > 1 for part in parts):
                    return name
        
        return None
    
    def _extract_title_near_email(self, text, email):
        """Try to extract a job title near the email address."""
        # Look for titles in the text near the email
        email_position = text.find(email)
        if email_position >= 0:
            # Check a reasonable context before and after the email
            context_start = max(0, email_position - 100)
            context_end = min(len(text), email_position + 100)
            context = text[context_start:context_end]
            
            # Look for title patterns
            titles = self.title_pattern.findall(context)
            
            # Return the first title found
            if titles:
                return titles[0]
        
        return None
    
    def _extract_links(self, base_url, soup, depth):
        """Extract links from the page to follow."""
        # Prioritize links that may contain contact information
        priority_links = []
        regular_links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '').strip()
            
            # Skip empty links and javascript
            if not href or href.startswith(('javascript:', 'mailto:', 'tel:')):
                continue
            
            # Convert relative URLs to absolute
            full_url = urljoin(base_url, href)
            
            # Skip non-HTTP protocols
            if not full_url.startswith(('http://', 'https://')):
                continue
            
            # Check if the link might contain contact information
            link_text = a_tag.get_text().lower()
            
            is_priority = False
            for keyword in self.target_keywords:
                if keyword.lower() in link_text or keyword.lower() in full_url.lower():
                    is_priority = True
                    break
            
            if is_priority:
                priority_links.append(full_url)
            else:
                regular_links.append(full_url)
        
        # Add priority links first
        for link in priority_links:
            self._add_url_to_queue(link, depth, priority=True)
        
        # Then regular links
        for link in regular_links:
            self._add_url_to_queue(link, depth, priority=False)

    def create_contacts_from_results(self, company):
        """
        Create Contact objects from scraping results
        
        Args:
            company: Company object to associate contacts with
            
        Returns:
            List of created Contact objects
        """
        created_contacts = []
        
        for email_data in self.results['emails'].values():
            email = email_data['email']
            
            # Check if this contact already exists
            try:
                contact = Contact.objects.get(email=email)
                # Update existing contact if needed
                if not contact.company:
                    contact.company = company
                    contact.save()
                created_contacts.append(contact)
                continue
            except Contact.DoesNotExist:
                pass
            
            # Extract name parts if available
            first_name = ''
            last_name = ''
            if 'name' in email_data:
                name_parts = email_data['name'].split()
                if name_parts:
                    first_name = name_parts[0]
                    if len(name_parts) > 1:
                        last_name = ' '.join(name_parts[1:])
            
            # If no name found, try to get from email
            if not first_name:
                username = email.split('@')[0]
                if '.' in username:
                    name_parts = username.split('.')
                    if len(name_parts) >= 2:
                        first_name = name_parts[0].title()
                        last_name = name_parts[1].title()
            
            # Create the contact
            contact = Contact(
                first_name=first_name,
                last_name=last_name,
                email=email,
                position=email_data.get('title', ''),
                company=company,
                source_channel=Contact.SourceChannel.SCRAPED,
                status=Contact.ContactStatus.NEW,
                organization_name=company.name
            )
            contact.save()
            created_contacts.append(contact)
        
        return created_contacts


def wait_for_any(futures):
    """
    Wait for any of the futures to complete.
    
    Args:
        futures: Set of futures to wait on
        
    Returns:
        Tuple of (done, not_done) futures
    """
    if not futures:
        return set(), set()
    
    done = set()
    while not done:
        for future in list(futures):
            if future.done():
                done.add(future)
                futures.remove(future)
        
        if done:
            break
        
        time.sleep(0.1)  # Short sleep to avoid CPU spinning
    
    return done, futures