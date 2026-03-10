#!/usr/bin/env python3
"""
PMC Keyword Search — PMCID Extractor

Searches PubMed Central's open access database for articles relevant to
cybersecurity and psychology research (deception, manipulation, fraud, etc.).

How it works:
  - Runs one search query per keyword category so each topic gets its fair
    share of results rather than competing in one big pool
  - Pulls the title + abstract for each result and checks them locally
  - Anything that triggers an exclusion keyword gets sidelined automatically
  - Matching PMCIDs are written out as we go, so you don't lose progress
    if something crashes halfway through

Needs: requests, lxml
NCBI asks for an API key if you're doing more than 3 req/s — we have one,
so we're capped at ~9/s to stay well under their limit.
"""

import requests
import time
import os
import sys
from datetime import datetime
from lxml import etree
from collections import Counter


# --- credentials ---
# NCBI gives you 10 req/s with a key vs 3 without, so always keep this set
API_KEY = "khkjhkjhkjhkjh"
EMAIL   = "kjbkjhkhkjkh"


# ---------------------------------------------------------------------------
# Main switches
# ---------------------------------------------------------------------------

# flip this off if you want to skip the search phase and just reprocess
# an existing PMCID list manually
ENABLE_KEYWORD_SEARCH = True

# how many results to pull back per category — each category gets its own
# esearch call, so this is the per-topic cap, not the overall total
RESULTS_PER_CATEGORY = 1000


# ---------------------------------------------------------------------------
# Output files — everything lands in a timestamped folder so reruns don't
# clobber each other
# ---------------------------------------------------------------------------
TIMESTAMP        = datetime.now().strftime('%Y%m%d_%H%M%S')
OUTPUT_FOLDER    = f"pmc_search_results_{TIMESTAMP}"
MATCHED_PMCIDS_FILE = os.path.join(OUTPUT_FOLDER, f"matched_pmcids_{TIMESTAMP}.txt")
EXCLUDED_FILE    = os.path.join(OUTPUT_FOLDER, f"excluded_health_{TIMESTAMP}.txt")
LOG_FILE         = os.path.join(OUTPUT_FOLDER, f"search_log_{TIMESTAMP}.txt")
STATISTICS_FILE  = os.path.join(OUTPUT_FOLDER, f"statistics_{TIMESTAMP}.txt")


# ---------------------------------------------------------------------------
# Rate limiting / retry settings
# ---------------------------------------------------------------------------

# 0.11s between calls keeps us at ~9 req/s — just under NCBI's limit of 10
DELAY_BETWEEN_REQUESTS = 0.11
MAX_RETRIES = 2

# set to False if you only want the log file and not stdout noise
VERBOSE_LOGGING = True

# NCBI's esearch URLs break silently if they get too long, so we split large
# keyword lists into chunks. 30 per chunk keeps the URL comfortably short
# even with long multi-word phrases
KEYWORDS_PER_CHUNK = 30


# ---------------------------------------------------------------------------
# Exclusion keywords
# Articles containing any of these in the title/abstract get filtered out.
# Useful for removing purely clinical papers that happen to share vocab with
# our psych/security topics (e.g. "deception" in a neurology context).
# ---------------------------------------------------------------------------
EXCLUDE_KEYWORDS = [
    # examples: "clinical trial", "patient outcomes", "hospital", "diagnosis"
]


# ---------------------------------------------------------------------------
# Keyword lists — fill these in before running
# ---------------------------------------------------------------------------

# cyber-side: attacks, threat actors, defensive tech, that kind of thing
CYBERSECURITY_KEYWORDS = [
    # e.g. "phishing", "social engineering", "pretexting", "spear phishing"
]

# psychology side — split into sub-topics so each one gets its own search
# quota and we can see which areas are producing results in the stats file

# deceptive practices in advertising, brand dishonesty, that kind of thing
BUSINESS_MARKETING_DECEPTION = [
    # e.g. "deceptive advertising", "greenwashing", "misleading claims"
]

# nudges, framing effects, irrational decision making
CONSUMER_BEHAVIORAL_ECONOMICS = [
    # e.g. "nudge", "choice architecture", "loss aversion"
]

# interpersonal manipulation, dark triad personality traits, coercion
PSYCHOLOGICAL_MANIPULATION = [
    # e.g. "gaslighting", "dark triad", "Machiavellianism", "coercive control"
]

# fraud, scams, con artistry, white collar crime
CRIMINOLOGY_FRAUD = [
    # e.g. "fraud", "confidence trick", "identity theft", "elder fraud"
]

# how cognitive limitations make people susceptible — attention, memory, bias
HUMAN_FACTORS_COGNITIVE = [
    # e.g. "cognitive bias", "bounded rationality", "inattentional blindness"
]

# misinformation, propaganda, persuasion through media channels
COMMUNICATION_MEDIA = [
    # e.g. "misinformation", "fake news", "disinformation", "propaganda"
]

# deception in workplace / org settings — whistleblowing, corporate fraud
ORGANIZATIONAL_MANAGEMENT = [
    # e.g. "organizational deception", "corporate fraud", "whistleblowing"
]


# ---------------------------------------------------------------------------
# Category registry
# This is what drives the search loop — one entry per category, each gets
# its own esearch call with up to RESULTS_PER_CATEGORY results.
# To add a new category just append a tuple here (and define its list above).
# ---------------------------------------------------------------------------
CATEGORY_REGISTRY = [
    ("Cybersecurity",               CYBERSECURITY_KEYWORDS),
    ("Business & Marketing",        BUSINESS_MARKETING_DECEPTION),
    ("Consumer & Behavioral Econ",  CONSUMER_BEHAVIORAL_ECONOMICS),
    ("Psychological Manipulation",  PSYCHOLOGICAL_MANIPULATION),
    ("Criminology & Fraud",         CRIMINOLOGY_FRAUD),
    ("Human Factors & Cognitive",   HUMAN_FACTORS_COGNITIVE),
    ("Communication & Media",       COMMUNICATION_MEDIA),
    ("Organizational Management",   ORGANIZATIONAL_MANAGEMENT),
]

NUM_CATEGORIES = len(CATEGORY_REGISTRY)

# flatten all psych lists into one for use during the local matching step
PSYCHOLOGY_KEYWORDS = (
    BUSINESS_MARKETING_DECEPTION +
    CONSUMER_BEHAVIORAL_ECONOMICS +
    PSYCHOLOGICAL_MANIPULATION +
    CRIMINOLOGY_FRAUD +
    HUMAN_FACTORS_COGNITIVE +
    COMMUNICATION_MEDIA +
    ORGANIZATIONAL_MANAGEMENT
)

# master list used when checking fetched abstracts — deduped so we don't
# count a hit twice if a keyword appears in multiple sub-categories
ALL_KEYWORDS = list(set(CYBERSECURITY_KEYWORDS + PSYCHOLOGY_KEYWORDS))

# theoretical maximum if every category fills up completely
MAX_SEARCH_RESULTS = RESULTS_PER_CATEGORY * NUM_CATEGORIES


# ---------------------------------------------------------------------------
# NCBI's esearch has an unofficial URL length limit. If you dump 200 quoted
# phrases into one query string it either errors out or silently truncates.
# This splits the list into chunks and returns one query string per chunk.
# ---------------------------------------------------------------------------
def build_chunked_queries(keyword_list, chunk_size=KEYWORDS_PER_CHUNK):
    chunks = []
    for i in range(0, len(keyword_list), chunk_size):
        batch = keyword_list[i : i + chunk_size]
        terms = [f'"{kw}"[Title/Abstract]' for kw in batch]
        chunks.append(" OR ".join(terms))
    return chunks


class PMCKeywordSearcher:
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

        self.total_searched          = 0
        self.matched_pmcids          = []
        self.excluded_pmcids         = {}  # pmcid -> list of exclusion kws that fired
        self.keyword_matches         = Counter()  # which target kws came up most
        self.exclude_keyword_matches = Counter()  # which exclusion kws fired most
        self.category_hit_counts     = Counter()  # new unique IDs contributed per category

        os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    def log(self, message):
        """Write to both console and log file with a timestamp prefix."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        if VERBOSE_LOGGING:
            print(log_msg)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')

    def _esearch_one_query(self, query, retmax):
        """
        Fire off a single esearch and return whatever PMCIDs come back.
        Returns an empty list rather than raising so the caller can keep going.

        Note: not using usehistory=y here — an earlier version had it set but
        we never consumed the WebEnv/query_key it returns, so it was just
        wasting a server-side history slot for nothing.
        """
        params = {
            "db":      "pmc",
            "term":    query,
            "retmax":  retmax,
            "retmode": "json",
            "api_key": API_KEY,
            "email":   EMAIL,
        }
        try:
            resp = requests.get(f"{self.base_url}esearch.fcgi", params=params, timeout=30)
            resp.raise_for_status()
            return resp.json().get("esearchresult", {}).get("idlist", [])
        except Exception as e:
            self.log(f"  WARNING: esearch request failed — {e}")
            return []

    def search_pmc_by_keywords(self):
        """
        Run one search per category and collect PMCIDs.

        Each category gets its own esearch call so the result quota is spread
        evenly. A single combined query would let popular keywords dominate
        and starve niche topics of their results.

        Large keyword lists get split into URL-safe chunks — all chunks are
        searched and their results merged before moving to the next category.

        PMCIDs are deduplicated across categories as we go, so an article
        that matches both "phishing" and "cognitive bias" only gets processed
        once later.
        """
        if not ENABLE_KEYWORD_SEARCH:
            self.log("Keyword search is disabled, skipping.")
            return []

        self.log("\n" + "=" * 80)
        self.log("STARTING PMC SEARCH  (one esearch call per category)")
        self.log("=" * 80)

        # bail out early if someone forgot to fill in the keyword lists
        if not ALL_KEYWORDS:
            self.log("ERROR: all keyword lists are empty — nothing to search for.")
            self.log("Fill in at least one of the keyword lists near the top of the file.")
            sys.exit(1)

        seen    = set()   # tracks IDs we've already added to avoid duplicates
        all_ids = []      # final ordered list, one entry per unique PMCID

        for label, kw_list in CATEGORY_REGISTRY:
            if not kw_list:
                self.log(f"  [skip] '{label}' — keyword list is empty")
                continue

            self.log(f"\n  Category: '{label}'  ({len(kw_list)} keywords)")

            chunks  = build_chunked_queries(kw_list)
            cat_ids = set()

            for chunk_query in chunks:
                # divide the per-category budget evenly across however many
                # chunks we needed — avoids over-fetching on chunked categories
                chunk_retmax = max(1, RESULTS_PER_CATEGORY // len(chunks))
                ids = self._esearch_one_query(chunk_query, chunk_retmax)
                cat_ids.update(ids)
                time.sleep(DELAY_BETWEEN_REQUESTS)

            # only keep IDs we haven't seen in a previous category
            new_ids = [pid for pid in cat_ids if pid not in seen]
            seen.update(new_ids)
            all_ids.extend(new_ids)

            self.category_hit_counts[label] = len(new_ids)
            self.log(f"    {len(cat_ids)} found, {len(new_ids)} new after dedup")

        self.log(f"\nTotal unique PMCIDs to process: {len(all_ids)}")
        self.total_searched = len(all_ids)
        return all_ids

    def fetch_title_and_abstract(self, pmcid):
        """
        Pull the XML record for one article and extract title + abstract text.
        Returns two strings — if either element is missing we just return
        an empty string for that field rather than crashing.
        """
        params = {
            "db":      "pmc",
            "id":      pmcid,
            "retmode": "xml",
            "api_key": API_KEY,
            "email":   EMAIL,
        }
        resp = requests.get(f"{self.base_url}efetch.fcgi", params=params, timeout=30)
        resp.raise_for_status()

        # recover=True keeps us moving even if the XML is slightly malformed
        root = etree.fromstring(resp.content, etree.XMLParser(recover=True))

        title_el = root.find('.//article-meta/title-group/article-title')
        title    = ''.join(title_el.itertext()).strip() if title_el is not None else ""

        abs_el   = root.find('.//article-meta/abstract')
        abstract = ''.join(abs_el.itertext()).strip() if abs_el is not None else ""

        return title, abstract

    def check_keywords_match(self, text):
        """Return the subset of ALL_KEYWORDS found in text (case-insensitive)."""
        if not text:
            return []
        lowered = text.lower()
        return [kw for kw in ALL_KEYWORDS if kw.lower() in lowered]

    def check_exclusion_keywords(self, text):
        """Return any exclusion keywords found in text. These take priority —
        if any fire, we don't bother checking for target keywords at all."""
        if not text:
            return []
        lowered = text.lower()
        return [kw for kw in EXCLUDE_KEYWORDS if kw.lower() in lowered]

    def process_pmcids(self, pmcid_list):
        """
        Main processing loop — fetch each article and decide what to do with it.

        Order of operations per article:
          1. fetch title + abstract
          2. check exclusion keywords first (health/clinical topic filter)
          3. if not excluded, check target keywords
          4. if matched, write the PMCID to the output file immediately
             so we don't lose anything if the script dies halfway through

        Failed fetches get retried with exponential backoff. After MAX_RETRIES
        the article is just skipped and logged — better to miss one than hang
        the whole run.
        """
        self.log(f"\nProcessing {len(pmcid_list)} articles...")

        matched_count = excluded_count = failed_count = 0

        for idx, pmcid in enumerate(pmcid_list, 1):
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    title, abstract = self.fetch_title_and_abstract(pmcid)
                    text = f"{title} {abstract}"

                    # exclusion check goes first — no point doing keyword matching
                    # on something we're going to throw away anyway
                    exclude_hits = self.check_exclusion_keywords(text)
                    if exclude_hits:
                        excluded_count += 1
                        self.excluded_pmcids[pmcid] = exclude_hits
                        for kw in exclude_hits:
                            self.exclude_keyword_matches[kw] += 1
                        self.log(
                            f"  ✗ [{idx}/{len(pmcid_list)}] PMC{pmcid}  "
                            f"excluded ({', '.join(exclude_hits[:3])})"
                        )
                    else:
                        kw_hits = self.check_keywords_match(text)
                        if kw_hits:
                            matched_count += 1
                            self.matched_pmcids.append(pmcid)
                            for kw in kw_hits:
                                self.keyword_matches[kw] += 1
                            # write immediately so progress is saved continuously
                            with open(MATCHED_PMCIDS_FILE, 'a', encoding='utf-8') as f:
                                f.write(f"PMC{pmcid}\n")
                            self.log(
                                f"  ✓ [{idx}/{len(pmcid_list)}] PMC{pmcid}  "
                                f"matched ({len(kw_hits)} keywords)"
                            )
                        else:
                            self.log(f"  - [{idx}/{len(pmcid_list)}] PMC{pmcid}  no match")

                    time.sleep(DELAY_BETWEEN_REQUESTS)
                    break  # success, move on to the next article

                except Exception as e:
                    if attempt >= MAX_RETRIES:
                        failed_count += 1
                        self.log(
                            f"  ! [{idx}/{len(pmcid_list)}] PMC{pmcid}  "
                            f"gave up after {MAX_RETRIES} attempts: {e}"
                        )
                    else:
                        time.sleep(2 ** attempt)  # exponential backoff: 2s, 4s, ...

            # progress snapshot every 100 so you can tell it's still alive
            if idx % 100 == 0:
                self.log(
                    f"\n  -- {idx}/{len(pmcid_list)} done | "
                    f"matched: {matched_count} | excluded: {excluded_count} | failed: {failed_count} --\n"
                )

        self.log(f"\n{'='*80}")
        self.log(f"done — matched: {matched_count} | excluded: {excluded_count} | failed: {failed_count}")
        self.log(f"{'='*80}")

    def write_excluded_list(self):
        """Dump the list of excluded PMCIDs and which keywords triggered each one.
        Handy for tuning the exclusion list — if a keyword is firing too often
        or not enough, it'll be obvious from this file."""
        if not self.excluded_pmcids:
            return
        with open(EXCLUDED_FILE, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("EXCLUDED PMCIDs\n")
            f.write("=" * 80 + "\n")
            f.write(f"Total excluded: {len(self.excluded_pmcids)}\n\n")
            for pmcid, kws in sorted(self.excluded_pmcids.items()):
                f.write(f"PMC{pmcid} : {', '.join(kws)}\n")
        self.log(f"Excluded list -> {EXCLUDED_FILE}")

    def write_statistics_report(self):
        """
        Write a summary of everything that happened this run: hit counts per
        category, most-matched keywords, most-triggered exclusion terms, and
        the overall match rate.

        Useful for spotting keyword drift over time — if a category that used
        to return hundreds of results suddenly drops to zero, something in the
        keyword list probably needs refreshing.
        """
        with open(STATISTICS_FILE, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("PMC KEYWORD SEARCH — STATISTICS\n")
            f.write("=" * 80 + "\n")
            f.write(f"Run completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Output folder: {OUTPUT_FOLDER}/\n\n")

            f.write("=" * 80 + "\n")
            f.write("SUMMARY\n")
            f.write("=" * 80 + "\n")
            f.write(f"Total articles processed : {self.total_searched:,}\n")
            f.write(f"Matched (kept)           : {len(self.matched_pmcids):,}\n")
            f.write(f"Excluded (health filter) : {len(self.excluded_pmcids):,}\n")

            # guard against divide-by-zero if we somehow got zero results back
            if self.total_searched > 0:
                rate = len(self.matched_pmcids) / self.total_searched * 100
                f.write(f"Match rate               : {rate:.2f}%\n")
            else:
                f.write("Match rate               : N/A\n")
            f.write("\n")

            f.write("=" * 80 + "\n")
            f.write("UNIQUE PMCIDs ADDED PER CATEGORY\n")
            f.write("=" * 80 + "\n")
            for label, _ in CATEGORY_REGISTRY:
                count = self.category_hit_counts.get(label, 0)
                f.write(f"  {label:<40} {count:>6,}\n")
            f.write("\n")

            f.write("=" * 80 + "\n")
            f.write("SEARCH CONFIG\n")
            f.write("=" * 80 + "\n")
            f.write(f"Results per category : {RESULTS_PER_CATEGORY:,}\n")
            f.write(f"Categories           : {NUM_CATEGORIES}\n")
            f.write(f"Keyword chunk size   : {KEYWORDS_PER_CHUNK}\n")
            f.write(f"\nKeyword counts:\n")
            f.write(f"  All (deduped)        : {len(ALL_KEYWORDS):,}\n")
            f.write(f"  Cybersecurity        : {len(CYBERSECURITY_KEYWORDS):,}\n")
            f.write(f"  Psychology total     : {len(PSYCHOLOGY_KEYWORDS):,}\n")
            f.write(f"    Business/Marketing : {len(BUSINESS_MARKETING_DECEPTION)}\n")
            f.write(f"    Consumer/BehEcon   : {len(CONSUMER_BEHAVIORAL_ECONOMICS)}\n")
            f.write(f"    Psych Manipulation : {len(PSYCHOLOGICAL_MANIPULATION)}\n")
            f.write(f"    Criminology/Fraud  : {len(CRIMINOLOGY_FRAUD)}\n")
            f.write(f"    Human Factors      : {len(HUMAN_FACTORS_COGNITIVE)}\n")
            f.write(f"    Comms/Media        : {len(COMMUNICATION_MEDIA)}\n")
            f.write(f"    Org/Management     : {len(ORGANIZATIONAL_MANAGEMENT)}\n")
            f.write(f"  Exclusion keywords   : {len(EXCLUDE_KEYWORDS):,}\n\n")

            if self.keyword_matches:
                f.write("=" * 80 + "\n")
                f.write("TOP 50 MATCHED KEYWORDS\n")
                f.write("=" * 80 + "\n")
                top = sorted(self.keyword_matches.items(), key=lambda x: x[1], reverse=True)
                for kw, count in top[:50]:
                    f.write(f"  {kw:<40} {count:>6,}\n")
                f.write(f"\n  {len(self.keyword_matches)} unique keywords matched in total\n\n")

            if self.exclude_keyword_matches:
                f.write("=" * 80 + "\n")
                f.write("TOP 50 EXCLUSION KEYWORDS (most triggered)\n")
                f.write("=" * 80 + "\n")
                top_ex = sorted(self.exclude_keyword_matches.items(), key=lambda x: x[1], reverse=True)
                for kw, count in top_ex[:50]:
                    f.write(f"  {kw:<40} {count:>6,}\n")
                f.write(f"\n  {len(self.exclude_keyword_matches)} unique exclusion keywords triggered\n\n")

            f.write("=" * 80 + "\n")
            f.write("END OF REPORT\n")
            f.write("=" * 80 + "\n")

        self.log(f"Stats report -> {STATISTICS_FILE}")

    def run(self):
        self.log("=" * 80)
        self.log("PMC KEYWORD SEARCH")
        self.log("=" * 80)
        self.log(f"Saving to: {OUTPUT_FOLDER}/")
        self.log(f"  {RESULTS_PER_CATEGORY:,} results/category × {NUM_CATEGORIES} categories = {MAX_SEARCH_RESULTS:,} max")
        self.log(f"  keyword chunk size: {KEYWORDS_PER_CHUNK}")
        self.log("=" * 80)

        self.log("\n[1/3] searching PMC...")
        pmcid_list = self.search_pmc_by_keywords()

        if not pmcid_list:
            self.log("no results came back — check your keyword lists and try again.")
            return

        self.log("\n[2/3] fetching and checking abstracts...")
        self.process_pmcids(pmcid_list)

        self.log("\n[3/3] writing output files...")
        self.write_excluded_list()
        self.write_statistics_report()

        self.log("\n" + "=" * 80)
        self.log("all done!")
        self.log("=" * 80)
        self.log(f"files written to {OUTPUT_FOLDER}/:")
        self.log(f"  {os.path.basename(MATCHED_PMCIDS_FILE)}  ({len(self.matched_pmcids)} matched PMCIDs)")
        self.log(f"  {os.path.basename(EXCLUDED_FILE)}  ({len(self.excluded_pmcids)} excluded)")
        self.log(f"  {os.path.basename(STATISTICS_FILE)}")
        self.log(f"  {os.path.basename(LOG_FILE)}")
        self.log("=" * 80)


if __name__ == "__main__":
    searcher = PMCKeywordSearcher()
    searcher.run()