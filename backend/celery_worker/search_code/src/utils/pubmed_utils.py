import logging
import csv

import os
# Configure the logger for this module
logger = logging.getLogger(__name__)


def load_retrieved_pmids(filepath: str) -> set:
    """
    Loads previously retrieved PMIDs from a CSV file into a set.

    Args:
        filepath: The path to the CSV file.

    Returns:
        A set containing all PMIDs from the file. Returns an empty set
        if the file does not exist or is empty.
    """
    if not os.path.exists(filepath):
        logging.info(f"📄 PMID file not found at '{filepath}'. Starting with an empty set.")
        return set()
    
    try:
        with open(filepath, mode='r', newline='', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            header = next(reader, None)
            if header != ['PMID']:
                logging.warning(f"⚠️ PMID file at '{filepath}' has an incorrect header or is empty. Starting fresh.")
                return set()
            pmids = {row[0] for row in reader if row}
            logging.info(f"✅ Successfully loaded {len(pmids)} PMIDs from '{filepath}'.")
            return pmids
    except (IOError, csv.Error) as e:
        logging.error(f"❌ Could not read existing PMID file at '{filepath}'. Starting fresh. Error: {e}")
        return set()

def save_retrieved_pmids(filepath: str, pmids: set):
    """
    Saves a set of PMIDs to a CSV file, overwriting any existing content.

    Args:
        filepath: The path to the CSV file.
        pmids: A set of PMIDs to save.
    """
    try:
        with open(filepath, mode='w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(['PMID'])  # Write header
            for pmid in sorted(list(pmids)): # Save in sorted order for consistency
                writer.writerow([pmid])
        logging.info(f"💾 Successfully saved {len(pmids)} PMIDs to '{filepath}'.")
    except IOError as e:
        logging.error(f"❌ Could not write to PMID file at '{filepath}'. Error: {e}")