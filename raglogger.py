import requests
import json
import time
import os
import re
from datetime import datetime
from lxml import etree
import hashlib
from collections import Counter

# API Credentials
API_KEY = "khkjhkjhkjh"
EMAIL = "kjhkjhkj"

# Input files
PMCID_FILES = ["khkjhkjhkjhkj"]

# Output configuration
OUTPUT_FILE = f"pmc_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
LOG_FILE = f"download_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

# Quality filters
MIN_WORD_COUNT = 500
MIN_SECTION_COUNT = 1

# Technical settings
DELAY_BETWEEN_REQUESTS = 0.11
MAX_RETRIES = 3
ENABLE_RESUME = True
VERBOSE_LOGGING = True

# Sections to skip (RAG-optimized)
SKIP_SECTIONS = {
    'references', 'bibliography', 'competing interests', 'conflict of interest',
    'author contributions', 'authors contributions', 'funding', 'acknowledgments',
    'acknowledgements', 'supplementary', 'abbreviations', 'data availability',
    'ethics statement', 'ethics approval', 'consent', 'supporting information',
    'disclosure', 'financial disclosure', 'copyright', 'author information',
    'availability', 'ethics', 'consent for publication'
}

# ============================================================================
# CYBERSECURITY KEYWORDS (Optimized with root forms)
# ============================================================================
CYBERSECURITY_KEYWORDS = [
    "scam", "fraud", "phish", "hack", "attack", "threat", "vulnerab",
    "cyber", "security", "insecur", "malware", "malicious", "spoof",
    "imperson", "access control", "account takeover", "dark triad", 
    "dark tetrad", "personality traits", "API security", "attack surface", 
    "baiting", "black hat", "botnet", "brute force", "buffer overflow", 
    "snake oil", "business email compromise", "code injection", "command and control",
    "credential harvest", "cross-site", "crypto miner", "cyber attack", 
    "cyber criminal", "cyber defense", "victimiz", "victim", "cyber extortion", 
    "cyber fraud", "cyber hygiene", "cyber resilien", "cyber scam", "cyber threat", 
    "data breach", "data exfiltrat", "data leak", "data protection", 
    "drive-by download", "encrypt", "exfiltrat", "firmware attack", "hijack", 
    "identity fraud", "identity management", "identity theft", 
    "insider threat", "intrus", "keylogger", "lateral movement", "loader", 
    "malicious actor", "malicious attachment", "malicious payload", 
    "malicious request", "malicious software", "man-in-the-middle", 
    "misconfigur", "MITM", "online fraud", "online imperson", "online scam", 
    "OT security", "password spray", "patching failure", "PII", "pretext", 
    "privilege escalat", "ransomware", "remote access trojan", "rootkit", 
    "script kiddie", "ai fraud", "ai crime", "security audit", "security flaw", 
    "security posture", "session fixation", "session hijack", "shoulder surf", 
    "SIEM", "smish", "social engineer", "spearphish", "spyware", 
    "SQL injection", "URL attack", "state-sponsored", "tailgat", "TCP/IP", 
    "threat actor", "threat detect", "threat intelligen", "trojan", "vish",
    "vulnerability assess", "weak authentication", "weak encryption", "whal", 
    "worm", "XSS", "zero-day", "zero day", "account suspension", 
    "verification request", "security alert", "unauthorized activity", 
    "suspicious login", "payment failure", "tech support scam", "refund scam", 
    "invoice scam", "romance scam", "password reset", "account verification", 
    "two-factor authentication", "multi-factor", "brand imperson", "logo spoof",
    "domain spoof", "typosquatt", "homograph attack", "punycode",
    "CEO fraud", "executive imperson", "wire transfer fraud", "fake invoice", 
    "payment redirect", "vendor imperson", "deepfake", "voice clon", 
    "ai imperson", "synthetic identity", "reciproc", "fomo", "fear of missing out"
]

# ============================================================================
# PSYCHOLOGY KEYWORDS (Optimized with root forms)
# ============================================================================

# Business & Marketing Deception
BUSINESS_MARKETING_DECEPTION = [
    "market", "advertis", "misinform", "false advertis", "misleading advertis",
    "social media marketing", "SMMA", "snake oil", "fake news", 
    "brand imperson", "logo spoof", "fake review", "astroturf", 
    "review manipulat", "fake expertise", "false credential", "bait and switch", 
    "limited time offer", "exclusive access", "artificial scarcity", 
    "scarcity principle", "exclusive opportunity", "rare opportunity", 
    "get rich quick", "easy money"
]

# Consumer Behavior & Behavioral Economics
CONSUMER_BEHAVIORAL_ECONOMICS = [
    "behavio", "bounded rationality", "decision fatigue", "decision science", 
    "decision-making error", "heuristic", "cognitive shortcut", "mental shortcut", 
    "satisfic", "anchor", "primacy anchor", "adjustment bias", "availability bias",
    "availability heuristic", "availability cascade", "familiarity heuristic",
    "framing effect", "message fram", "loss fram", "gain fram", "reference point", 
    "loss aversion", "status quo bias", "status quo effect", "endowment effect", 
    "sunk cost", "escalat", "default bias", "cognitive bias", "bias",
    "judgment bias", "confirmation bias", "confirmation trap", "hindsight bias",
    "overconfiden", "optimism bias", "recency bias", "primacy effect", 
    "serial position", "frequency bias", "base rate neglect", "conjunction fallacy", 
    "gambler's fallacy", "hot hand fallacy", "illusion of control", 
    "illusory correlation", "clustering illusion", "regression to the mean", 
    "outcome bias", "survivorship bias", "selection bias", "self-serving bias", 
    "attribution bias", "attribution error", "fundamental attribution error", 
    "choice overload", "choice architecture", "decision paralysis", 
    "paralysis by analysis", "information overload", "mental accounting", 
    "compartmentaliz", "peak-end rule", "duration neglect", "focalism", 
    "impact bias", "affective forecast", "empathy gap", "projection bias",
    "planning fallacy", "false consensus", "dunning-kruger", "cognitive dissonance",
    "reactance", "normalcy bias", "just-world hypothesis", "apophenia", "pareidolia",
    "pattern recognition", "motivated reasoning", "wishful thinking", 
    "magical thinking", "belief perseveran", "backfire effect", 
    "motivated skeptic", "motivated credulit"
]

# Psychological Manipulation & Interpersonal Deception
PSYCHOLOGICAL_MANIPULATION = [
    "manipulat", "deceiv", "deception", "exploit", "influence", "persuad", 
    "persuasion", "coerce", "coercion", "trick", "trickery", "dupe", "duping",
    "conned", "conning", "con artist", "swindle", "swindl", "cheat", 
    "trust", "distrust", "mistrust", "credib", "incredible", "abuse", "abus",
    "psychological manipulation", "emotional manipulation", 
    "financial manipulation", "behavioral manipulation", "social manipulation", 
    "interpersonal manipulation", "narrative manipulation", "context manipulation", 
    "manipulative personalit", "criminal deception", "intentional deception", 
    "deceptive behavio", "physical deception", "misdirect", "smoke screen", 
    "reality distortion", "confusion tactic", "gaslight", "compulsive liar", 
    "machiavell", "psychopath", "narcissistic trait", "dark triad", "darktriad", 
    "dark tetrad", "dark personality", "exploitative individual", 
    "exploitative motivation", "interpersonal scam", "socially engineered fraud", 
    "fraudulent communication", "fraudulent persuasion", "fraudulent request", 
    "trust exploitation", "trust violation", "trust cue", "trust formation", 
    "interpersonal trust", "borrowed trust", "trust transfer", "halo transfer", 
    "reputation hijack", "identity fabricat", "persona creation", 
    "impersonation attack", "false sense of urgency", "urgency cue", 
    "urgency exploit", "time pressure", "deadline pressure", "deadline technique", 
    "emergency fram", "panic induction", "fear monger", "catastrophiz", 
    "fear appeal", "appeal to fear", "emotional arousal", "emotional trigger", 
    "emotional language", "emotional vulnerab", "emotional susceptib", 
    "emotional dependen", "emotional distress", "emotional instability", 
    "guilt induction", "guilt trip", "shame induction", "shame exploit", 
    "embarrassment threat", "humiliation threat", "sympathy appeal", "pity play", 
    "empathy exploit", "loneliness exploit", "isolation exploit", "grief exploit", 
    "desperation exploit", "vulnerability target", "dependency creation", 
    "codependen", "love bombing", "idealiz", "devaluat", "triangulat",
    "isolation tactic", "mirror", "pacing and leading", "rapport exploit",
    "rapport build", "language match", "neuro-linguistic programming", "nlp",
    "embedded command", "presupposition", "implication", "vague language",
    "ambiguity", "double bind", "pride manipulat", "ego strok", "flatter",
    "compliment", "greed exploit", "fomo", "fear of missing out",
    "regret aversion", "hope exploit", "obligation induction", "debt creation"
]

# Criminology & Fraud Studies
CRIMINOLOGY_FRAUD = [
    "scam complian", "scam message", "prize notification", "lottery", 
    "sweepstakes", "inheritance", "advance fee fraud", "419 scam", 
    "nigerian prince", "social media scam", "catfish", "romance fraud",
    "romance scam", "investment scam", "ponzi scheme", "pyramid scheme",
    "cryptocurrency scam", "crypto fraud", "nft scam", "charity fraud",
    "donation scam", "disaster relief scam", "tax scam", "IRS imperson",
    "government imperson", "package delivery scam", "shipping notification",
    "tracking scam", "job scam", "employment fraud", "work from home scam",
    "overpayment scam", "check fraud", "money mule", "criminal", "extortion", 
    "sextortion", "blackmail", "ransom demand", "wire transfer fraud", 
    "CEO fraud", "executive imperson", "fake invoice", "payment redirect", 
    "vendor imperson", "business email compromise", "invoice scam",
    "refund scam", "tech support scam", "victimiz", "victim", 
    "fraud victim", "victim blam", "attribution of blame"
]

# Human Factors & Cognitive Psychology
HUMAN_FACTORS_COGNITIVE = [
    "cognitiv", "cognition", "cognitive psychology", "cognitive bias",
    "cognitive impair", "cognitive overload", "cognitive load", 
    "cognitive dissonance", "cognitive shortcut", "working memory",
    "attention deficit", "reduced attention", "dual process theory", "system 1", 
    "system 2", "heuristic process", "systematic process", 
    "elaboration likelihood", "peripheral route", "central route",
    "multitask", "impaired judgment", "altered judgment", "rationality error", 
    "fatigue", "decision fatigue", "stress", "stress susceptib", "anxiety", 
    "depression", "emotional distress", "dissociat", "impulsiv", "habituat", 
    "sensitiv", "arousal", "activation", "learned helplessness", 
    "locus of control", "self-efficacy", "risk perception", "sensation seek", 
    "reward sensit", "psychological vulnerab", "social vulnerab", "susceptib",
    "susceptibility to persuasion", "neuroticism", "agreeableness", 
    "conscientiousness", "introversion", "extraversion", "personality psychology",
    "motivation", "motivation and affect", "control motivation", 
    "dominance motivation", "exploitative motivation", "attachment insecur", 
    "attachment pattern", "loneliness", "social isolation", "anonymity",
    "submissiv", "dependen", "illusion of invulnerab"
]

# Communication & Media Studies
COMMUNICATION_MEDIA = [
    "linguistic cue", "loaded language", "euphemism", "dysphemism", 
    "weasel words", "glittering generalit", "name calling", "red herring",
    "strawman", "false dilemma", "slippery slope", "appeal to emotion",
    "appeal to authority", "appeal to tradition", "appeal to novelty",
    "testimonial", "transfer technique", "third-party endorse", 
    "celebrity endorse", "influencer fraud", "credentials display", 
    "authority symbol", "uniform", "title", "source credibility", "persuasion", "persuade"
    "expertise cue", "trustworthiness", "authority mimic", "credibility cue", 
    "fake news", "misinform", "mislead", "false advertis", "misleading advertis",
    "narrative persuasion", "persuasive messag", "persuasive language",
    "persuasion strateg", "message fram", "emergency fram"
]

# Organizational Behavior / Management
ORGANIZATIONAL_MANAGEMENT = [
    "comply", "complian", "obey", "obedien", "conform", "conformity", "conformist",
    "social conformity", "group influence", "group norm", "peer pressure",
    "social pressure", "normative influence", "informational influence",
    "social influence", "social bond", "social proof", "social validation",
    "consensus", "popularity cue", "trending", "bandwagon effect", "bandwagon",
    "groupthink", "risky shift", "polariz", "social proof fabrication",
    "authority exploit", "authority influence", "authority pressure",
    "hierarchical pressure", "power dynamic", "power imbalance", "dominance",
    "commitment", "consistency", "commitment principle", "consistency principle",
    "public commitment", "written commitment", "commitment trap", 
    "consistency trap", "foot-in-the-door", "door-in-the-face", "low-ball technique",
    "that's-not-all", "disrupt-then-reframe", "reciproc", "reciprocity norm", 
    "reciprocal concession", "gift giving", "liking", "liking principle", 
    "similarity attraction", "similarity bias", "attractiveness bias", 
    "mere exposure effect", "scarcity", "identity alignment", "self-perception", 
    "behavioral condition", "operant condition", "classical condition", 
    "pavlovian condition", "reinforcement", "vicarious reinforcement", 
    "intermittent reinforcement", "variable reward", "unpredictable reward", 
    "punishment", "social learning", "observational learning", 
    "modeling", "priming", "nudging", "behavioral influence", "behavioral pattern", 
    "relational influence", "interpersonal influence", "interpersonal conflict", 
    "influence operation", "influence tactic", "influence technique", 
    "undue influence", "affective influence", "habit loop", "halo effect", 
    "decoy effect", "contrast effect", "phantom fixation", "anchor", 
    "sequential request", "cultural factor", "collectivism", "stereotype", 
    "prejudice", "implicit bias", "explicit bias", "in-group bias", "out-group bias", 
    "self-fulfilling prophecy", "social psychology", "psychology", "psychological", 
    "psychologist", "moral psychology", "emotion", "social", "societal",
    "expected behavior", "legitimate request mimic", "routine request", 
    "process exploit", "policy exploit", "procedure bypass", "helpfulness exploit",
    "politeness exploit", "courtesy trap", "reciprocation pressure",
    "social obligation", "situational pressure", "time constraint", 
    "resource constraint", "warning fatigue", "alert fatigue", "security fatigue", 
    "password fatigue", 
    "desensitiz", "habituation to warning", "security theater", "security hygiene", 
    "security awareness", "risk compensation", "risk homeostasis", "peltzman effect"
]

# Combine all psychology keywords
PSYCHOLOGY_KEYWORDS = (
    BUSINESS_MARKETING_DECEPTION +
    CONSUMER_BEHAVIORAL_ECONOMICS +
    PSYCHOLOGICAL_MANIPULATION +
    CRIMINOLOGY_FRAUD +
    HUMAN_FACTORS_COGNITIVE +
    COMMUNICATION_MEDIA +
    ORGANIZATIONAL_MANAGEMENT
)

# Combine all keywords for theme detection (cyber + psych)
ALL_KEYWORDS = list(set(CYBERSECURITY_KEYWORDS + PSYCHOLOGY_KEYWORDS))


class RAGOptimizedPMCDownloader:
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.processed_ids = set()
        self.failed_ids = []
        self.progress_file = "download_progress.json"
        self.total_processed = 0
        self.seen_hashes = set()  # For deduplication
        
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
    
    def save_progress(self):
        """Save current progress"""
        if ENABLE_RESUME:
            with open(self.progress_file, 'w') as f:
                json.dump({
                    'processed_ids': list(self.processed_ids),
                    'failed_ids': self.failed_ids,
                    'total_processed': self.total_processed
                }, f)
    
    def load_progress(self):
        """Load previous progress"""
        try:
            with open(self.progress_file, 'r') as f:
                progress = json.load(f)
                self.processed_ids = set(progress.get('processed_ids', []))
                self.failed_ids = progress.get('failed_ids', [])
                self.total_processed = progress.get('total_processed', 0)
                self.log(f"Resumed: {len(self.processed_ids)} articles already processed")
        except Exception as e:
            self.log(f"Could not load progress: {e}")
    
    def load_pmcids_from_files(self):
        """Load PMCIDs from text files"""
        all_pmcids = []
        
        for file_path in PMCID_FILES:
            try:
                with open(file_path, 'r') as f:
                    file_pmcids = []
                    for line in f:
                        pmcid = line.strip()
                        if pmcid.upper().startswith("PMC"):
                            pmcid = pmcid[3:]
                        if pmcid and pmcid.isdigit():
                            file_pmcids.append(pmcid)
                    
                    all_pmcids.extend(file_pmcids)
                    self.log(f"  Loaded {len(file_pmcids)} PMCIDs from {file_path}")
            
            except FileNotFoundError:
                self.log(f"  WARNING: File {file_path} not found")
            except Exception as e:
                self.log(f"  ERROR loading {file_path}: {e}")
        
        # Remove duplicates
        unique_pmcids = list(dict.fromkeys(all_pmcids))
        if len(all_pmcids) != len(unique_pmcids):
            self.log(f"  Removed {len(all_pmcids) - len(unique_pmcids)} duplicate PMCIDs")
        
        self.log(f"Total unique PMCIDs: {len(unique_pmcids)}")
        return unique_pmcids
    
    def aggressive_clean_text(self, text):
        """Aggressively clean text for RAG (optimized for retrieval quality)"""
        if not text:
            return ""
        
        # Remove LaTeX/TeX markup
        text = re.sub(r'\\documentclass\{[^}]*\}', '', text)
        text = re.sub(r'\\usepackage\{[^}]*\}', '', text)
        text = re.sub(r'\\begin\{document\}', '', text)
        text = re.sub(r'\\end\{document\}', '', text)
        text = re.sub(r'\\setlength\{[^}]*\}\{[^}]*\}', '', text)
        text = re.sub(r'\$\$[^\$]*\$\$', '', text)  # $$formula$$
        text = re.sub(r'\$[^\$]*\$', '', text)  # $formula$
        text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text)  # \command{arg}
        text = re.sub(r'\\[a-zA-Z]+', '', text)  # \command
        
        # Remove soft hyphens and fix hyphenated line breaks
        text = text.replace('\u00ad', '')
        text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
        
        # Normalize quotes and dashes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('—', '-').replace('–', '-')
        
        # Remove citation markers
        text = re.sub(r'\s*\[[0-9,\-\s]+\]', '', text)
        text = re.sub(r'\([A-Za-z\s]+et al\.,?\s*\d{4}[a-z]?\)', '', text)
        text = re.sub(r'\([A-Z][a-z]+\s*(?:&|and)\s*[A-Z][a-z]+,?\s*\d{4}[a-z]?\)', '', text)
        
        # Remove empty brackets/parentheses
        text = re.sub(r'\[\s*\]', '', text)
        text = re.sub(r'\(\s*\)', '', text)
        
        # Remove figure/table references
        text = re.sub(r'\(Fig\.?\s*\d*\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\(Table\s*\d*\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\(see\s+(?:Fig\.|Table)[^)]*\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(?:Figure|Table)\s+\d+', '', text, flags=re.IGNORECASE)
        
        # Remove supplementary references
        text = re.sub(r'\(see\s+Supplementary[^)]+\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\(Supplementary[^)]+\)', '', text, flags=re.IGNORECASE)
        
        # Remove common boilerplate phrases
        boilerplate = [
            r'Downloaded from.*?on \d+',
            r'© \d{4}.*?(?:Authors|Publishers)',
            r'This article is distributed.*?license',
            r'Ethical approval was obtained.*?\.',
            r'All participants provided.*?consent\.',
            r'This work was supported by.*?\.'
        ]
        for pattern in boilerplate:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Keep UTF-8 for mathematical symbols and accented characters
        text = text.encode('utf-8', errors='ignore').decode('utf-8')
        
        return text.strip()
    
    def count_keywords_in_text(self, text):
        """
        Efficiently count all keyword occurrences in text and return top 4.
        Uses Counter for optimal performance.
        """
        if not text:
            return []
        
        text_lower = text.lower()
        keyword_counts = Counter()
        
        # Count each keyword occurrence
        for keyword in ALL_KEYWORDS:
            keyword_lower = keyword.lower()
            count = text_lower.count(keyword_lower)
            if count > 0:
                keyword_counts[keyword] = count
        
        # Return top 4 most frequent keywords
        if not keyword_counts:
            return []
        
        return [keyword for keyword, count in keyword_counts.most_common(4)]
    
    def get_element_text(self, elem):
        """Extract text from XML element, excluding unwanted sub-elements"""
        if elem is None:
            return ""
        
        # Remove unwanted elements (namespace-aware)
        for bad_tag in ['xref', 'table-wrap', 'fig', 'graphic', 'inline-graphic',
                        'media', 'supplementary-material', 'label', 'caption',
                        'disp-formula', 'inline-formula', 'tex-math', 
                        'alternatives', 'ref-list', 'ack']:
            for child in elem.xpath(f'.//*[local-name()="{bad_tag}"]'):
                parent = child.getparent()
                if parent is not None:
                    parent.remove(child)
        
        # Handle namespaced math elements
        for child in elem.xpath('.//*[local-name()="math"]'):
            parent = child.getparent()
            if parent is not None:
                parent.remove(child)
        
        text = ''.join(elem.itertext())
        return self.aggressive_clean_text(text)
    
    def should_skip_section(self, title):
        """Check if section should be skipped"""
        if not title:
            return False
        
        title_lower = title.lower().strip()
        return any(skip_term in title_lower for skip_term in SKIP_SECTIONS)
    
    def check_has_statistics(self, text):
        """Check if text contains statistical information"""
        if not text:
            return False
        
        stat_patterns = [
            r'p\s*[<>=]\s*0?\.\d+',  # p-values
            r'[rR]²?\s*=\s*0?\.\d+',  # R-squared
            r'd\s*=\s*\d+\.?\d*',  # Cohen's d
            r'[tTfF]\s*\(\d+\)\s*=\s*\d+\.?\d*',  # t-test, F-test
            r'χ²\s*=\s*\d+\.?\d*',  # chi-square
            r'(?:OR|HR|RR)\s*=\s*\d+\.?\d*',  # odds/hazard/risk ratio
            r'\d+\.?\d*\s*%'  # percentages
        ]
        
        return any(re.search(pattern, text) for pattern in stat_patterns)
    
    def is_duplicate_section(self, text):
        """Check if section is duplicate using hash"""
        if not text or len(text) < 50:
            return False
        
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.seen_hashes:
            return True
        
        self.seen_hashes.add(text_hash)
        return False
    
    def normalize_section_type(self, title, sec_type_attr):
        """Normalize section type for RAG metadata"""
        if not title:
            title = ""
        
        title_lower = title.lower()
        
        # Map to standardized section types
        if any(x in title_lower for x in ['abstract', 'summary']):
            return 'abstract'
        elif any(x in title_lower for x in ['introduction', 'background']):
            return 'introduction'
        elif any(x in title_lower for x in ['method', 'material', 'procedure', 'design']):
            return 'methods'
        elif any(x in title_lower for x in ['result', 'finding']):
            return 'results'
        elif any(x in title_lower for x in ['discussion', 'conclusion', 'implication']):
            return 'discussion'
        elif sec_type_attr:
            return sec_type_attr.lower()
        else:
            return 'other'
    
    def extract_section_recursive(self, sec_elem, paper_metadata):
        """Recursively extract sections with RAG-optimized metadata"""
        if sec_elem is None:
            return []
        
        sections = []
        
        # Get section title and type
        title_elem = sec_elem.find('.//title')
        section_title = self.aggressive_clean_text(
            title_elem.text if title_elem is not None and title_elem.text else ""
        )
        
        # Skip unwanted sections
        if self.should_skip_section(section_title):
            return []
        
        sec_type_attr = sec_elem.get('sec-type', '')
        if any(skip in sec_type_attr.lower() for skip in ['supplementary', 'table', 'figure']):
            return []
        
        # Extract text from this section only (not subsections)
        section_copy = etree.fromstring(etree.tostring(sec_elem))
        for nested_sec in section_copy.findall('.//sec'):
            if nested_sec != section_copy:
                nested_sec.getparent().remove(nested_sec)
        
        section_text = self.get_element_text(section_copy)
        
        # Skip if duplicate or too short
        if self.is_duplicate_section(section_text) or len(section_text.strip()) < 10:
            # Still process subsections
            for subsec in sec_elem.findall('./sec'):
                sections.extend(self.extract_section_recursive(subsec, paper_metadata))
            return sections
        
        # Normalize section type
        section_type = self.normalize_section_type(section_title, sec_type_attr)
        
        # Check for statistics
        has_statistics = self.check_has_statistics(section_text)
        
        # Build section with metadata
        section_data = {
            "type": section_type,
            "title": section_title or "Untitled",
            "text": section_text
        }
        
        # Add optional metadata if detected
        if has_statistics:
            section_data["has_statistics"] = True
        
        sections.append(section_data)
        
        # Process subsections
        for subsec in sec_elem.findall('./sec'):
            sections.extend(self.extract_section_recursive(subsec, paper_metadata))
        
        return sections
    
    def extract_abstract(self, root):
        """Extract abstract with metadata"""
        abstract_elem = root.find('.//article-meta/abstract')
        if abstract_elem is None:
            return None
        
        abstract_text = self.get_element_text(abstract_elem)
        if not abstract_text or len(abstract_text.strip()) < 10:
            return None
        
        section_data = {
            "type": "abstract",
            "title": "Abstract",
            "text": abstract_text
        }
        
        return section_data
    
    def extract_metadata(self, root):
        """Extract article metadata for RAG"""
        metadata = {}
        
        try:
            # Title
            title_elem = root.find('.//article-meta/title-group/article-title')
            if title_elem is not None:
                metadata["title"] = self.aggressive_clean_text(self.get_element_text(title_elem))
            
            # Authors (first 3 only for brevity)
            authors = []
            for contrib in root.xpath('.//article-meta/contrib-group/contrib[@contrib-type="author"]')[:3]:
                name = contrib.find('.//name')
                if name is not None:
                    surname = name.findtext('surname', '').strip()
                    given = name.findtext('given-names', '').strip()
                    if surname:
                        authors.append(f"{given} {surname}".strip())
            
            if authors:
                metadata["authors"] = authors
            
            # Journal
            journal_title = root.findtext('.//journal-meta//journal-title', '').strip()
            if journal_title:
                metadata["journal"] = journal_title
            
            # Publication year (critical for temporal filtering)
            pub_date = root.find('.//article-meta/pub-date[@pub-type="epub"]')
            if pub_date is None:
                pub_date = root.find('.//article-meta/pub-date')
            
            if pub_date is not None:
                year = pub_date.findtext('year', '').strip()
                if year:
                    try:
                        metadata["year"] = int(year)
                    except ValueError:
                        pass
            
            # DOI
            doi_elem = root.find('.//article-meta/article-id[@pub-id-type="doi"]')
            if doi_elem is not None and doi_elem.text:
                metadata["doi"] = doi_elem.text.strip()
            
        except Exception as e:
            self.log(f"  Warning: Metadata extraction error: {e}")
        
        return metadata
    
    def fetch_and_process_article(self, pmcid):
        """Fetch and process article with RAG-optimized structure"""
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
        
        # Parse XML with recover mode
        parser = etree.XMLParser(recover=True, remove_blank_text=True)
        root = etree.fromstring(response.content, parser=parser)
        
        # Remove unwanted elements globally (namespace-aware)
        for xpath_expr in [
            './/*[local-name()="ref-list"]',
            './/*[local-name()="table-wrap"]',
            './/*[local-name()="supplementary-material"]',
            './/*[local-name()="disp-formula"]',
            './/*[local-name()="inline-formula"]',
            './/*[local-name()="ack"]',
            './/*[local-name()="math"]'
        ]:
            for bad_elem in root.xpath(xpath_expr):
                parent = bad_elem.getparent()
                if parent is not None:
                    parent.remove(bad_elem)
        
        # Extract metadata first
        metadata = self.extract_metadata(root)
        
        # Extract all sections
        all_sections = []
        
        # Abstract
        abstract = self.extract_abstract(root)
        if abstract:
            all_sections.append(abstract)
        
        # Body sections
        body = root.find('.//body')
        if body is not None:
            for sec in body.findall('./sec'):
                sections = self.extract_section_recursive(sec, metadata)
                all_sections.extend(sections)
        
        # Apply quality filters
        total_words = sum(len(sec.get('text', '').split()) for sec in all_sections)
        
        if MIN_WORD_COUNT > 0 and total_words < MIN_WORD_COUNT:
            self.log(f"  Skipping PMC{pmcid}: only {total_words} words")
            return None
        
        if MIN_SECTION_COUNT > 0 and len(all_sections) < MIN_SECTION_COUNT:
            self.log(f"  Skipping PMC{pmcid}: only {len(all_sections)} sections")
            return None
        
        # Combine all text for paper-level keyword analysis
        full_text = metadata.get("title", "") + " " + " ".join(sec.get("text", "") for sec in all_sections)
        
        # Get top 4 keyword themes for the entire paper
        top_keywords = self.count_keywords_in_text(full_text)
        
        # Build output structure (RAG-optimized)
        result = {
            "paper_id": f"PMC{pmcid}",
            "title": metadata.get("title", ""),
            "year": metadata.get("year"),
            "theme": top_keywords if top_keywords else [],
            "abstract": next((s["text"] for s in all_sections if s["type"] == "abstract"), ""),
            "sections": all_sections,
            "word_count": total_words,
            "section_count": len(all_sections)
        }
        
        # Add optional metadata
        if "authors" in metadata:
            result["authors"] = metadata["authors"]
        if "journal" in metadata:
            result["journal"] = metadata["journal"]
        if "doi" in metadata:
            result["doi"] = metadata["doi"]
        
        # Check if any section has statistics
        has_any_stats = any(section.get("has_statistics") for section in all_sections)
        if has_any_stats:
            result["has_statistics"] = True
        
        return result
    
    def process_articles(self, id_list):
        """Process list of articles"""
        remaining_ids = [pid for pid in id_list if pid not in self.processed_ids]
        self.log(f"Processing {len(remaining_ids)} articles...")
        
        success_count = 0
        
        for idx, pmcid in enumerate(remaining_ids, 1):
            # Reset deduplication per article
            self.seen_hashes = set()
            
            retry_count = 0
            success = False
            
            while retry_count < MAX_RETRIES and not success:
                try:
                    article_data = self.fetch_and_process_article(pmcid)
                    
                    if article_data:
                        # Write to JSONL
                        with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                            json.dump(article_data, f, ensure_ascii=False)
                            f.write('\n')
                        
                        success_count += 1
                        
                        # Log with metadata
                        theme_str = f", theme: {article_data.get('theme', [])}" if article_data.get('theme') else ""
                        
                        self.log(f"  ✓ [{idx}/{len(remaining_ids)}] PMC{pmcid} "
                                f"({article_data['word_count']} words, "
                                f"{article_data['section_count']} sections"
                                f"{theme_str})")
                    
                    self.processed_ids.add(pmcid)
                    self.total_processed += 1
                    success = True
                    
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
                self.log(f"Progress: {success_count} successful, {len(self.failed_ids)} failed")
        
        self.log(f"Processing complete! {success_count} articles saved")
        if self.failed_ids:
            self.log(f"Failed: {len(self.failed_ids)} articles")
    
    def run(self):
        """Main execution"""
        self.log("=" * 70)
        self.log("RAG-Optimized PMC Downloader - Enhanced Version")
        self.log("=" * 70)
        
        # Load PMCIDs
        self.log(f"Reading PMCIDs from {len(PMCID_FILES)} file(s):")
        id_list = self.load_pmcids_from_files()
        
        if not id_list:
            self.log("No articles to process. Exiting.")
            return
        
        self.log(f"Configuration:")
        self.log(f"  Articles to process: {len(id_list)}")
        self.log(f"  Output: {OUTPUT_FILE}")
        self.log(f"  Min words: {MIN_WORD_COUNT}")
        self.log(f"  Total cyber keywords: {len(CYBERSECURITY_KEYWORDS)}")
        self.log(f"  Total psych keywords: {len(PSYCHOLOGY_KEYWORDS)}")
        self.log(f"  Theme detection: Top 4 most frequent keywords")
        self.log("=" * 70)
        
        # Process
        self.process_articles(id_list)
        
        # Stats
        if os.path.exists(OUTPUT_FILE):
            file_size = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
            self.log(f"Output size: {file_size:.2f} MB")
        
        # Cleanup
        if ENABLE_RESUME and os.path.exists(self.progress_file):
            os.remove(self.progress_file)
        
        if self.failed_ids:
            self.log(f"Failed PMCIDs: {', '.join(self.failed_ids[:20])}")
        
        self.log("=" * 70)
        self.log("Download Complete!")
        self.log("=" * 70)


if __name__ == "__main__":
    downloader = RAGOptimizedPMCDownloader()
    downloader.run()