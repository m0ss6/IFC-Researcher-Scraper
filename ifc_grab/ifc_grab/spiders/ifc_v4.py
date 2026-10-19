# Here we are only attempting to fix the grabbing of researcher's data inside the department "Bioquimica y Biologia Molecular" which seems to have a different structure due to having videos inside the page that might be interfering with the scraping. 

import scrapy
from urllib.parse import urljoin
from scrapy_playwright.page import PageMethod

class Ifc_v4(scrapy.Spider):
    def __init__(self, *args, **kwargs):
        super(Ifc_v4, self).__init__(*args, **kwargs)
        self.whole_scrape = {}
        self.scraped_data = []
        self.whole_scrape['Scrapped'] = self.scraped_data
        self.ongoing_links = {}
        self.department_lenghts = {}
        self.processed_count = 0

    name = 'ifc_v4'
    
    custom_settings = {
        'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
        'DOWNLOAD_HANDLERS': {
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 1,  # Be polite to the server
    }
    
    def start_requests(self):
        print('Starting the spider')
        # `-a start_url=...` takes precedence over the IFC_START_URL setting
        url = getattr(self, 'start_url', None) or self.settings.get('IFC_START_URL')

        yield scrapy.Request(
            url=url,
            meta={
                'playwright': True,
                'playwright_include_page': True,
                'playwright_page_methods': [
                    PageMethod('wait_for_selector', 'div[class*="contenedor-con-bordes"]', state='visible'),
                    PageMethod('wait_for_selector', 'div[class*="contenedor-con-bordes"] h2, '
                                                'div[class*="contenedor-con-bordes"] p, '
                                                'div[class*="contenedor-con-bordes"] a'),
                    PageMethod('wait_for_load_state', 'networkidle'),
                ],
            },
            callback=self.parse
        )

    async def parse(self, response):
        print('Entering first parse')
        containers = response.css('div[class*="contenedor-con-bordes"]')
        
        self.logger.info(f"Found {len(containers)} containers.")
        
        self.ongoing_links['First level links'] = []
        self.ongoing_links['Second level links'] = []
        
        for container in containers:
            title = container.css('a.text-5::text').get()
            if title:
                title = title.strip()
            
            relative_url = container.css('a.text-5::attr(href)').get()
            
            if relative_url and title:
                absolute_url = urljoin(response.url, relative_url)
                
                item = {
                    'title': title,
                    'url': absolute_url,
                    'relative_url': relative_url,
                    'Researchers': {}
                }
                
                self.scraped_data.append(item)
        
        page = response.meta['playwright_page']
        await page.close()
        
        print(f'Total departments collected: {len(self.scraped_data)}')
        
        for i in self.scraped_data:
            self.ongoing_links['First level links'].append(i.get("url"))
        
        print('Ongoing links dictionary:', self.ongoing_links)
        
        print('Entering second request')
        
        for link in self.scraped_data:
            print(f"Processing department: {link['title']}")
            
            yield scrapy.Request(
                url=link['url'], 
                callback=self.second_parse, 
                meta={
                    'data': link,
                    'playwright': True,
                    'playwright_page_methods': [
                        # Wait for the EXACT card class, not just any card-body
                        PageMethod('wait_for_selector', 'div.card-body7', state='attached', timeout=10000),
                        # Or wait for researcher links specifically
                        PageMethod('wait_for_selector', 'div.card-body7 a', state='attached', timeout=10000),
                        # Optional: Scroll a bit to trigger lazy loading
                        PageMethod('evaluate', 'window.scrollBy(0, 500)'),
                        PageMethod('wait_for_timeout', 1000),
                    ]
                }
            )

    async def second_parse(self, second_response):
        print('Entering second parse')
        division_data = second_response.meta['data']
        
        print(f'\nProcessing department: {division_data.get("title", "Unknown")}')
        text_block = second_response.css('div[class*="card-body"]')
        
        if text_block:
            print('Found the desired text block with researchers')
            
            for block in text_block:
                researcher_name_elem = block.css('a::text').get()
                if researcher_name_elem:
                    researcher_name = str(researcher_name_elem.strip())
                    
                    # Initialize researcher entry
                    division_data['Researchers'][researcher_name] = {}
                    
                    researcher_link = block.css('a::attr(href)').get()
                    if researcher_link:
                        absolute_researcher_link = urljoin(second_response.url, researcher_link)
                        
                        print(f'  Found researcher: {researcher_name}')
                        division_data['Researchers'][researcher_name]['Researcher link'] = absolute_researcher_link
                        self.ongoing_links['Second level links'].append(absolute_researcher_link)
        
        print(f'\nTotal researchers found in this department: {len(division_data["Researchers"])}')
        
        page = second_response.meta.get('playwright_page')
        if page:
            await page.close()
        
        print('Exiting second parse')
        
        # Print summary of all data collected so far
        self.print_data_summary()
        
        # Now initiate third level requests for all researchers
        print('\n' + '='*50)
        print('STARTING THIRD LEVEL CRAWLING (Researcher Profiles)')
        print('='*50)
        
        total_researchers = sum(len(dept.get('Researchers', {})) for dept in self.scraped_data)
        print(f'Total researchers to process: {total_researchers}')
        
        # Process all departments and researchers
        for dept_index, department in enumerate(self.scraped_data):
            if 'Researchers' in department and department['Researchers']:
                for researcher_name, researcher_data in department['Researchers'].items():
                    profile_link = researcher_data.get('Researcher link')
                    
                    if profile_link:
                        # Prepare meta data to identify where to store the results
                        meta_info = {
                            'department_index': dept_index,
                            'researcher_name': researcher_name,
                            'department_title': department.get('title', 'Unknown'),
                            'playwright': True,
                            'playwright_page_methods': [
                                PageMethod('wait_for_selector', 'div[class="col-lg-12"]', 
                                state='visible', timeout=10000),

                                PageMethod('wait_for_selector','p[class="post-info-s font-weight-light pb-3.5 mb-0 lh-1-7 fontz-15"]', 

                                state='visible', timeout=10000),
                                PageMethod('wait_for_load_state', 'networkidle'),
                            ]
                        }
                        
                        yield scrapy.Request(
                            url=profile_link,
                            callback=self.third_parse,
                            meta=meta_info,
                            errback=self.errback_third_parse
                        )
                    else:
                        print(f'Warning: No profile link for {researcher_name}')
    
    def print_data_summary(self):
        """Print summary of collected data"""
        print(f"\n{'='*60}")
        print("DATA COLLECTION SUMMARY")
        print(f"{'='*60}")
        
        total_researchers = 0
        for idx, dept in enumerate(self.scraped_data):
            researchers = dept.get('Researchers', {})
            researcher_count = len(researchers)
            total_researchers += researcher_count
            print(f"Department {idx+1}: {dept.get('title', 'Unknown')}")
            print(f"  URL: {dept.get('url', 'N/A')}")
            print(f"  Researchers: {researcher_count}")
            
            # List researchers in this department
            for i, (name, data) in enumerate(list(researchers.items())[:5]):  # Show first 5
                print(f"    {i+1}. {name}")
            if researcher_count > 5:
                print(f"    ... and {researcher_count - 5} more")
            print()
        
        print(f"TOTAL: {len(self.scraped_data)} departments, {total_researchers} researchers")
        print(f"{'='*60}\n")

    async def third_parse(self, third_response):
        print('\n' + '-'*40)
        print('Entering third parse (Researcher Profile)')
        
        # Get identifying information from meta
        dept_index = third_response.meta['department_index']
        researcher_name = third_response.meta['researcher_name']
        department_title = third_response.meta['department_title']
        
        print(f'Processing: {researcher_name}')
        print(f'Department: {department_title} (Index: {dept_index})')
        print(f'Profile URL: {third_response.url}')
        
        # Look for the exact info block using the class you specified
        info_block = third_response.css('div[class="col-lg-12"]')
        mightb_mail = third_response.css('p[class="post-info-s font-weight-light pb-3.5 mb-0 lh-1-7 fontz-15"]::text')
        
        email = None

        if mightb_mail:
            print('Found possibly an email address block!')
            email_text = mightb_mail.get() 
            
            # Validate it's actually an email
            if email_text and '@' in email_text and '.' in email_text:
                email = email_text.strip()
                print(f'  Extracted email: {email}')
            else:
                print('  Found text block but it doesn\'t look like an email')
                
                # Try alternative email extraction methods
                # Look for email in any text on the page using regex
                import re
                email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                
                # Check the specific block first
                if email_text:
                    potential_emails = re.findall(email_pattern, email_text)
                    if potential_emails:
                        email = potential_emails[0]
                        print(f'  Extracted email using regex from text block: {email}')
                
                # If still not found, search the entire page body
                if not email:
                    all_text = third_response.css('body ::text').getall()
                    combined_text = ' '.join(all_text)
                    potential_emails = re.findall(email_pattern, combined_text)
                    if potential_emails:
                        # Take the first unique email
                        unique_emails = list(set(potential_emails))
                        if unique_emails:
                            email = unique_emails[0]
                            print(f'  Found email in page text: {email}')
        
        # If still no email, mark as not found
        if not email:
            print('  No email address found for this researcher')

        researcher_info_text = None
        
        if info_block:
            print('Found the exact researcher info block!')
            
            # Extract all text from this block
            raw_text = info_block.css('::text').getall()
            
            # Clean and filter the text
            cleaned_info = []
            for text in raw_text:
                cleaned = text.strip()
                if cleaned:  # Only keep non-empty strings
                    cleaned_info.append(cleaned)
            
            if cleaned_info:
                researcher_info_text = cleaned_info
                print(f'Extracted {len(cleaned_info)} text segments from info block')
            else:
                print('Warning: Info block found but no text content extracted')
                researcher_info_text = []
        else:
            print('Warning: Exact info block not found, trying alternative selectors...')
            
            # Try alternative selectors in case of class variations
            alternative_selectors = [
                'div[class*="post-info-s"]',
                'div[class*="font-weight-light"][class*="pb-3"]',
                'div.post-info-s',
                '.post-info-s',
                'div.fontz-15',
                'div[class*="fontz-15"]'
            ]
            
            for selector in alternative_selectors:
                alt_block = third_response.css(selector)
                if alt_block:
                    print(f'Found info with alternative selector: {selector}')
                    raw_text = alt_block.css('::text').getall()
                    
                    cleaned_info = []
                    for text in raw_text:
                        cleaned = text.strip()
                        if cleaned:
                            cleaned_info.append(cleaned)
                    
                    if cleaned_info:
                        researcher_info_text = cleaned_info
                        print(f'Extracted {len(cleaned_info)} text segments using alternative selector')
                        break
        
        # Update the data structure with the extracted info
        if researcher_info_text is not None:
            try:
                # Find the correct department
                if dept_index < len(self.scraped_data):
                    department = self.scraped_data[dept_index]
                    
                    # Find the correct researcher in this department
                    if researcher_name in department.get('Researchers', {}):
                        # Add the researcher info
                        department['Researchers'][researcher_name]['researcher info'] = researcher_info_text
                        
                        # Add the email if found
                        if email:
                            department['Researchers'][researcher_name]['email'] = email
                            print(f'✓ Email added for {researcher_name}: {email}')
                        else:
                            department['Researchers'][researcher_name]['email'] = None
                            print(f'✗ No email found for {researcher_name}')
                        
                        self.processed_count += 1
                        print(f'✓ Successfully added info for {researcher_name}')
                        print(f'Total researchers processed: {self.processed_count}')
                        
                        # Optional: Print a sample of the extracted info
                        if researcher_info_text and len(researcher_info_text) > 0:
                            sample = researcher_info_text[0][:100] + "..." if len(researcher_info_text[0]) > 100 else researcher_info_text[0]
                            print(f'  Sample info: {sample}')
                    else:
                        print(f'Error: Researcher {researcher_name} not found in department {dept_index}')
                else:
                    print(f'Error: Department index {dept_index} out of range')
            except Exception as e:
                print(f'Error updating data structure: {e}')
        else:
            print(f'Could not extract info for {researcher_name}')
            # Still create an entry with email if found
            try:
                if dept_index < len(self.scraped_data):
                    department = self.scraped_data[dept_index]
                    if researcher_name in department.get('Researchers', {}):
                        department['Researchers'][researcher_name]['researcher info'] = []
                        department['Researchers'][researcher_name]['extraction_failed'] = True
                        
                        # Still add email if found
                        if email:
                            department['Researchers'][researcher_name]['email'] = email
                            print(f'✓ Email added even though info extraction failed: {email}')
                        else:
                            department['Researchers'][researcher_name]['email'] = None
                        
                        self.processed_count += 1
            except Exception as e:
                print(f'Error creating fallback entry: {e}')
        
        # Close Playwright page
        page = third_response.meta.get('playwright_page')
        if page:
            await page.close()
        
        print('Exiting third parse')
        print('-'*40 + '\n')
    
    def errback_third_parse(self, failure):
        """Handle errors in third parse requests"""
        print('\nERROR in third parse request:')
        print(f'   URL: {failure.request.url}')
        print(f'   Error: {failure.value}')
        
        # Try to extract which researcher failed from meta
        if hasattr(failure.request, 'meta'):
            researcher_name = failure.request.meta.get('researcher_name', 'Unknown')
            dept_index = failure.request.meta.get('department_index', -1)
            print(f'   Researcher: {researcher_name}')
            print(f'   Department index: {dept_index}')
            
            # Mark as failed in data structure
            try:
                if dept_index >= 0 and dept_index < len(self.scraped_data):
                    department = self.scraped_data[dept_index]
                    if researcher_name in department.get('Researchers', {}):
                        department['Researchers'][researcher_name]['request_failed'] = True
                        department['Researchers'][researcher_name]['error'] = str(failure.value)
            except Exception as e:
                print(f'   Error updating failure status: {e}')
    
    def closed(self, reason):
        # Final summary
        print('\n' + '='*60)
        print('SPIDER CLOSING - FINAL SUMMARY')
        print('='*60)
        
        total_researchers = 0
        researchers_with_info = 0
        researchers_failed = 0
        researchers_with_email = 0
        
        for idx, dept in enumerate(self.scraped_data):
            researchers = dept.get('Researchers', {})
            total_researchers += len(researchers)
            
            for researcher_name, data in researchers.items():
                if 'researcher info' in data and data['researcher info']:
                    researchers_with_info += 1
                
                if data.get('email'):
                    researchers_with_email += 1
                    
                if data.get('request_failed') or data.get('extraction_failed'):
                    researchers_failed += 1
        
        print(f"Departments: {len(self.scraped_data)}")
        print(f"Total researchers: {total_researchers}")
        print(f"Researchers with info extracted: {researchers_with_info}")
        print(f"Researchers with email found: {researchers_with_email}")
        print(f"Email collection rate: {(researchers_with_email/total_researchers*100):.1f}%" if total_researchers > 0 else "N/A")
        print(f"Researchers failed: {researchers_failed}")
        print(f"Success rate: {(researchers_with_info/total_researchers*100):.1f}%" if total_researchers > 0 else "N/A")
        
        # Save to JSON
        import json
        from pathlib import Path
        output_dir = Path(self.settings.get('OUTPUT_DIR', 'data'))
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / 'output.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_data, f, ensure_ascii=False, indent=2)

        print(f"\nSaved {len(self.scraped_data)} departments to {output_path}")
        print('='*60)