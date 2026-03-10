"""
PMC Title Extractor
Fetches PMCIDs and their article titles from PubMed Central
"""
import requests
import time
import os
import re
from datetime import datetime
import xmltodict

# ============================================================================
# CONFIGURATION
# ============================================================================

# API Credentials
API_KEY = "hkjhkjhkjhkjh" 
EMAIL = "jkhkjhkjhkjhjkh"

# Input Method - Get .txt files
PMCID_FILES = [
    "unique_pmcids_part1.txt",
    # Add more files as needed
]

# Output file
OUTPUT_FILE = f"pmc_titles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

# Technical Settings
DELAY_BETWEEN_REQUESTS = 0.11  # Seconds (0.1 = 10 req/s with API key)
MAX_RETRIES = 3
ENABLE_RESUME = True

# Logging
VERBOSE_LOGGING = True
LOG_FILE = f"download_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

# ============================================================================
# CODE
# ============================================================================

class PMCTitleExtractor:
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.processed_ids = set()
        self.failed_ids = []
        self.progress_file = "title_progress.json"
        
        if ENABLE_RESUME and os.path.exists(self.progress_file):
            self.load_progress()
    
    def log(self, message):
        """Log message to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        
        if VERBOSE_LOGGING:
            print(log_msg)
        
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    
    def load_progress(self):
        """Load previous progress"""
        try:
            import json
            with open(self.progress_file, 'r') as f:
                progress = json.load(f)
                self.processed_ids = set(progress.get('processed_ids', []))
                self.failed_ids = progress.get('failed_ids', [])
                self.log(f"Resumed: {len(self.processed_ids)} PMCIDs already processed")
        except Exception as e:
            self.log(f"Could not load progress: {e}")
    
    def save_progress(self):
        """Save current progress"""
        if ENABLE_RESUME:
            import json
            progress = {
                'processed_ids': list(self.processed_ids),
                'failed_ids': self.failed_ids
            }
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f)
    
    def load_pmcids_from_files(self):
        """Load PMCIDs from multiple text files"""
        all_pmcids = []
        
        for file_path in PMCID_FILES:
            try:
                with open(file_path, 'r') as f:
                    file_pmcids = []
                    for line in f:
                        pmcid = line.strip()
                        # Remove "PMC" prefix if present
                        if pmcid.upper().startswith("PMC"):
                            pmcid = pmcid[3:]
                        if pmcid and pmcid.isdigit():
                            file_pmcids.append(pmcid)
                    
                    all_pmcids.extend(file_pmcids)
                    self.log(f"  Loaded {len(file_pmcids)} PMCIDs from {file_path}")
            
            except FileNotFoundError:
                self.log(f"  WARNING: File {file_path} not found, skipping")
            except Exception as e:
                self.log(f"  ERROR loading {file_path}: {e}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_pmcids = []
        for pmcid in all_pmcids:
            if pmcid not in seen:
                seen.add(pmcid)
                unique_pmcids.append(pmcid)
        
        duplicates_removed = len(all_pmcids) - len(unique_pmcids)
        if duplicates_removed > 0:
            self.log(f"  Removed {duplicates_removed} duplicate PMCIDs")
        
        self.log(f"Total unique PMCIDs loaded: {len(unique_pmcids)}")
        return unique_pmcids
    
    def extract_text(self, node):
        """Recursively extract text from XML node"""
        if isinstance(node, str):
            text = node.replace("\n", " ").replace("\t", " ")
            text = re.sub(r"\s+", " ", text)
            return text.encode("ascii", errors="ignore").decode("ascii").strip()
        elif isinstance(node, dict):
            text_content = []
            for k, v in node.items():
                if k.startswith("@"):
                    continue
                text_content.append(self.extract_text(v))
            return " ".join(filter(None, text_content))
        elif isinstance(node, list):
            return " ".join(self.extract_text(i) for i in node)
        else:
            return ""
    
    def clean_text(self, text):
        """Clean extracted text"""
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    
    def fetch_title(self, pmcid):
        """Fetch article title for a single PMCID"""
        params = {
            "db": "pmc",
            "id": pmcid,
            "retmode": "xml",
            "api_key": API_KEY,
            "email": EMAIL
        }
        
        response = requests.get(f"{self.base_url}efetch.fcgi", params=params)
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")
        
        xml_data = response.text
        data_dict = xmltodict.parse(xml_data)
        
        try:
            article = data_dict["pmc-articleset"]["article"]
            article_meta = article.get("front", {}).get("article-meta", {})
            title_group = article_meta.get("title-group", {})
            
            if isinstance(title_group, dict):
                article_title = title_group.get("article-title", "")
                if article_title:
                    title = self.clean_text(self.extract_text(article_title))
                    return title
            
            return "No title found"
            
        except Exception as e:
            raise Exception(f"Extraction error: {e}")
    
    def process_pmcids(self, id_list):
        """Process list of PMCIDs and extract titles"""
        remaining_ids = [pid for pid in id_list if pid not in self.processed_ids]
        self.log(f"Processing {len(remaining_ids)} PMCIDs...")
        
        success_count = 0
        
        for idx, pmcid in enumerate(remaining_ids, 1):
            retry_count = 0
            success = False
            
            while retry_count < MAX_RETRIES and not success:
                try:
                    title = self.fetch_title(pmcid)
                    
                    # Write in the format: {PMCID} : Article Title
                    output_line = f"PMC{pmcid} : {title}\n"
                    
                    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                        f.write(output_line)
                    
                    success_count += 1
                    self.log(f"  ✓ [{idx}/{len(remaining_ids)}] PMC{pmcid}")
                    
                    self.processed_ids.add(pmcid)
                    success = True
                    
                    # Rate limiting
                    time.sleep(DELAY_BETWEEN_REQUESTS)
                
                except Exception as e:
                    retry_count += 1
                    self.log(f"  ✗ PMC{pmcid} failed (attempt {retry_count}/{MAX_RETRIES}): {e}")
                    
                    if retry_count < MAX_RETRIES:
                        time.sleep(2 ** retry_count)
                    else:
                        self.failed_ids.append(pmcid)
                        self.processed_ids.add(pmcid)
            
            # Save progress periodically
            if idx % 50 == 0:
                self.save_progress()
                self.log(f"Progress checkpoint: {success_count} successful, {len(self.failed_ids)} failed")
        
        self.log(f"Processing complete! Successfully extracted {success_count} titles")
        if self.failed_ids:
            self.log(f"Failed to download {len(self.failed_ids)} PMCIDs")
    
    def run(self):
        """Main execution flow"""
        self.log("=" * 60)
        self.log("PMC Title Extractor Started")
        self.log("=" * 60)
        
        # Get PMCIDs from files
        self.log(f"Reading PMCIDs from {len(PMCID_FILES)} file(s):")
        id_list = self.load_pmcids_from_files()
        
        if not id_list:
            self.log("No PMCIDs to process. Exiting.")
            return
        
        self.log(f"Configuration:")
        self.log(f"  Total PMCIDs to process: {len(id_list)}")
        self.log(f"  Output file: {OUTPUT_FILE}")
        self.log("=" * 60)
        
        # Process PMCIDs
        self.process_pmcids(id_list)
        
        # Calculate final file size
        if os.path.exists(OUTPUT_FILE):
            file_size = os.path.getsize(OUTPUT_FILE) / 1024
            self.log(f"Output file size: {file_size:.2f} KB")
        
        # Clean up progress file
        if ENABLE_RESUME and os.path.exists(self.progress_file):
            os.remove(self.progress_file)
        
        if self.failed_ids:
            self.log(f"Failed PMCIDs: {', '.join(['PMC' + fid for fid in self.failed_ids[:20]])}")
        
        self.log("=" * 60)
        self.log("Extraction Complete!")
        self.log("=" * 60)


if __name__ == "__main__":
    extractor = PMCTitleExtractor()
    extractor.run()