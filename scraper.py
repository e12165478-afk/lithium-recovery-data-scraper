#!/usr/bin/env python3
"""
GitHub Data Scraper for Lithium Recovery & Desalination Research
Searches all public repos and aggregates data into structured CSV.

Usage:
    export GITHUB_TOKEN='ghp_xxxxx'
    python scraper.py
"""

import os
import json
import pandas as pd
import numpy as np
import requests
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import logging
from urllib.parse import urljoin
import re
import time
from tqdm import tqdm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GitHubDataScraper:
    """
    Scrapes GitHub for lithium recovery, brine, and desalination research data.
    """
    
    def __init__(self, github_token: str = None):
        """
        Args:
            github_token: Personal access token for higher rate limits
        """
        self.github_token = github_token or os.getenv('GITHUB_TOKEN', '')
        self.session = requests.Session()
        if self.github_token:
            self.session.headers.update({'Authorization': f'token {self.github_token}'})
            logger.info("✓ GitHub token configured (higher rate limits)")
        else:
            logger.warning("⚠ No GitHub token found. Rate limits: 60 req/hr (vs 5000 with token)")
            logger.info("  To increase limits: export GITHUB_TOKEN='ghp_xxxxx'")
        
        self.base_url = 'https://api.github.com'
        self.raw_url = 'https://raw.githubusercontent.com'
        self.all_data = []
        
        # Keywords to search for
        self.search_keywords = [
            'lithium recovery brine',
            'lithium extraction desalination',
            'DLE adsorption',
            'lithium from seawater',
            'brine treatment',
            'lithium carbonate',
            'ion exchange resin',
            'reverse osmosis brine',
            'produced water lithium',
            'geothermal brine',
        ]
        
        # Column name mapping
        self.column_mapping = {
            # Lithium
            'li': 'li_ppm', 'lithium': 'li_ppm', 'li_ppm': 'li_ppm',
            'li_mg_l': 'li_ppm', 'li_concentration': 'li_ppm',
            
            # Sodium
            'na': 'na_ppm', 'sodium': 'na_ppm', 'na_ppm': 'na_ppm',
            
            # Potassium
            'k': 'k_ppm', 'potassium': 'k_ppm', 'k_ppm': 'k_ppm',
            
            # Magnesium
            'mg': 'mg_ppm', 'magnesium': 'mg_ppm', 'mg_ppm': 'mg_ppm',
            
            # Calcium
            'ca': 'ca_ppm', 'calcium': 'ca_ppm', 'ca_ppm': 'ca_ppm',
            
            # Chloride
            'cl': 'cl_ppm', 'chloride': 'cl_ppm', 'cl_ppm': 'cl_ppm',
            
            # Sulfate
            'so4': 'so4_ppm', 'sulfate': 'so4_ppm', 'so4_ppm': 'so4_ppm',
            
            # TDS
            'tds': 'tds_ppm', 'total_dissolved_solids': 'tds_ppm', 'tds_ppm': 'tds_ppm',
            
            # pH
            'ph': 'ph_adjusted', 'ph_adjusted': 'ph_adjusted',
            
            # Temperature
            'temp': 'temperature_c', 'temperature': 'temperature_c', 'temperature_c': 'temperature_c',
            
            # Flow
            'flow': 'inlet_flow_m3hr', 'flow_rate': 'inlet_flow_m3hr',
            'flowrate': 'inlet_flow_m3hr', 'inlet_flow': 'inlet_flow_m3hr',
            
            # Pressure
            'pressure': 'operating_pressure_bar', 'operating_pressure': 'operating_pressure_bar',
            
            # Recovery
            'recovery': 'li_recovery_percent', 'recovery_percent': 'li_recovery_percent',
            'li_recovery': 'li_recovery_percent',
            
            # Purity
            'purity': 'li_product_purity_percent', 'product_purity': 'li_product_purity_percent',
            'assay': 'li_product_purity_percent',
        }
    
    def search_repositories(self, limit: int = 50) -> List[Dict]:
        """
        Search GitHub for relevant repositories.
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"STEP 1: Searching GitHub repositories")
        logger.info(f"{'='*70}")
        logger.info(f"Searching {len(self.search_keywords)} keywords (limit: {limit} repos per keyword)...\n")
        
        all_repos = []
        
        for keyword in self.search_keywords:
            query = f'q={keyword} type:repo'
            url = f'{self.base_url}/search/repositories?{query}&sort=stars&per_page={limit}'
            
            try:
                resp = self.session.get(url, timeout=10)
                resp.raise_for_status()
                
                data = resp.json()
                repos = data.get('items', [])
                
                logger.info(f"  ✓ '{keyword}': {len(repos)} repos found")
                all_repos.extend(repos)
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"  ✗ Error searching '{keyword}': {e}")
        
        # Deduplicate by repo ID
        unique_repos = {repo['id']: repo for repo in all_repos}
        logger.info(f"\n✓ Total unique repositories: {len(unique_repos)}")
        
        return list(unique_repos.values())
    
    def get_repo_files(self, repo: Dict) -> List[Dict]:
        """
        Get data files from a repository.
        """
        owner = repo['owner']['login']
        repo_name = repo['name']
        
        url = f'{self.base_url}/repos/{owner}/{repo_name}/contents'
        
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            contents = resp.json()
            
            files = []
            for item in contents:
                if item['type'] == 'file':
                    # Look for data files
                    if item['name'].endswith(('.csv', '.xlsx', '.json', '.ipynb')):
                        files.append({
                            'name': item['name'],
                            'path': item['path'],
                            'download_url': item['download_url'],
                            'repo': f"{owner}/{repo_name}",
                            'size': item.get('size', 0)
                        })
            
            return files
        
        except Exception as e:
            logger.warning(f"Error fetching files from {owner}/{repo_name}: {e}")
            return []
    
    def extract_csv_data(self, file_url: str, repo_name: str, file_name: str) -> List[Dict]:
        """
        Download and parse CSV file.
        """
        try:
            # Try to download
            resp = self.session.get(file_url, timeout=15)
            resp.raise_for_status()
            
            # Parse CSV
            from io import StringIO
            df = pd.read_csv(StringIO(resp.text), nrows=1000)
            
            # Convert to list of dicts
            records = df.to_dict('records')
            
            # Add provenance
            for record in records:
                record['_source_repo'] = repo_name
                record['_source_file'] = file_name
                record['_source_type'] = 'csv'
            
            return records
        
        except Exception as e:
            logger.debug(f"Error parsing CSV {file_url}: {e}")
            return []
    
    def extract_xlsx_data(self, file_url: str, repo_name: str, file_name: str) -> List[Dict]:
        """
        Download and parse Excel file.
        """
        try:
            # Download to temp
            import tempfile
            resp = self.session.get(file_url, timeout=15)
            resp.raise_for_status()
            
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name
            
            # Read Excel
            xls = pd.ExcelFile(tmp_path)
            
            all_records = []
            for sheet in xls.sheet_names[:3]:  # First 3 sheets
                df = pd.read_excel(tmp_path, sheet_name=sheet, nrows=500)
                records = df.to_dict('records')
                
                for record in records:
                    record['_source_repo'] = repo_name
                    record['_source_file'] = file_name
                    record['_source_sheet'] = sheet
                    record['_source_type'] = 'xlsx'
                
                all_records.extend(records)
            
            # Cleanup
            os.unlink(tmp_path)
            
            return all_records
        
        except Exception as e:
            logger.debug(f"Error parsing Excel {file_url}: {e}")
            return []
    
    def extract_json_data(self, file_url: str, repo_name: str, file_name: str) -> List[Dict]:
        """
        Download and parse JSON file.
        """
        try:
            resp = self.session.get(file_url, timeout=15)
            resp.raise_for_status()
            
            data = resp.json()
            
            # Try to extract records
            if isinstance(data, list):
                records = data
            elif isinstance(data, dict):
                # Try common keys
                for key in ['data', 'records', 'samples', 'results']:
                    if key in data:
                        records = data[key]
                        break
                else:
                    records = [data]
            else:
                return []
            
            # Add provenance
            for record in records:
                if isinstance(record, dict):
                    record['_source_repo'] = repo_name
                    record['_source_file'] = file_name
                    record['_source_type'] = 'json'
            
            return records
        
        except Exception as e:
            logger.debug(f"Error parsing JSON {file_url}: {e}")
            return []
    
    def normalize_record(self, record: Dict) -> Dict:
        """
        Normalize a single record to master schema.
        """
        norm_record = {}
        
        for key, value in record.items():
            if key.startswith('_'):
                # Keep metadata
                norm_record[key] = value
                continue
            
            # Normalize column name
            std_key = self.column_mapping.get(key.lower().strip(), key.lower().strip())
            
            # Skip if value is None or empty
            if value is None or (isinstance(value, str) and value.strip() == ''):
                continue
            
            # Type conversions
            try:
                if any(std_key.endswith(suffix) for suffix in ['_ppm', '_percent', '_c', '_bar', '_m3hr', '_min', '_days', '_cm3', '_cp', '_g_cm3']):
                    value = float(value)
                elif std_key in ['ph_raw', 'ph_adjusted']:
                    value = float(value)
            except (ValueError, TypeError):
                value = None
            
            if value is not None:
                norm_record[std_key] = value
        
        return norm_record
    
    def normalize_to_master_schema(self, records: List[Dict]) -> List[Dict]:
        """
        Normalize all extracted records to master schema.
        """
        logger.info(f"\nNormalizing {len(records)} records to master schema...")
        
        normalized = []
        
        for record in tqdm(records, desc="Normalizing", total=len(records)):
            norm_record = self.normalize_record(record)
            if norm_record:  # Only add non-empty records
                normalized.append(norm_record)
        
        logger.info(f"✓ Normalized to {len(normalized)} records")
        return normalized
    
    def scrape_all(self, repo_limit: int = 30) -> pd.DataFrame:
        """
        Main scraping workflow.
        """
        logger.info("\n" + "="*70)
        logger.info("LITHIUM RECOVERY DATA SCRAPER - MAIN WORKFLOW")
        logger.info("="*70)
        
        # Step 1: Search repositories
        repos = self.search_repositories(limit=repo_limit)
        
        if not repos:
            logger.error("✗ No repositories found!")
            return pd.DataFrame()
        
        # Step 2: Extract files from each repo
        logger.info(f"\n{'='*70}")
        logger.info(f"STEP 2: Extracting data files from repositories")
        logger.info(f"{'='*70}\n")
        
        for i, repo in enumerate(repos):
            logger.info(f"[{i+1}/{len(repos)}] {repo['full_name']} ⭐ {repo['stargazers_count']}")
            
            files = self.get_repo_files(repo)
            
            if not files:
                logger.info(f"  └─ No data files found")
                continue
            
            for file in files:
                if file['size'] > 10_000_000:  # Skip files > 10MB
                    logger.info(f"  └─ ⊘ {file['name']} (too large, {file['size']/1e6:.1f}MB)")
                    continue
                
                logger.info(f"  ├─ ⟳ {file['name']}", end='')
                
                records = []
                
                if file['name'].endswith('.csv'):
                    records = self.extract_csv_data(file['download_url'], repo['full_name'], file['name'])
                elif file['name'].endswith('.xlsx'):
                    records = self.extract_xlsx_data(file['download_url'], repo['full_name'], file['name'])
                elif file['name'].endswith('.json'):
                    records = self.extract_json_data(file['download_url'], repo['full_name'], file['name'])
                
                if records:
                    logger.info(f" → {len(records)} records ✓")
                    self.all_data.extend(records)
                else:
                    logger.info(f" → no valid data")
            
            time.sleep(2)  # Rate limiting
        
        # Step 3: Normalize to master schema
        logger.info(f"\n{'='*70}")
        logger.info(f"STEP 3: Normalizing data to master schema")
        logger.info(f"{'='*70}")
        
        normalized = self.normalize_to_master_schema(self.all_data)
        
        # Step 4: Create DataFrame
        logger.info(f"\n{'='*70}")
        logger.info(f"STEP 4: Building DataFrame")
        logger.info(f"{'='*70}\n")
        
        df = pd.DataFrame(normalized)
        
        # Step 5: Define master columns
        master_columns = [
            # Feed Chemistry
            'li_ppm', 'na_ppm', 'k_ppm', 'mg_ppm', 'ca_ppm', 
            'cl_ppm', 'so4_ppm', 'b_ppm', 'sr_ppm', 'ba_ppm', 'sio2_ppm',
            'tds_ppm', 'ph_raw', 'ph_adjusted', 'temperature_c', 
            'density_g_cm3', 'viscosity_cp', 'toc_ppm', 'oil_grease_ppm',
            
            # Process Conditions
            'inlet_flow_m3hr', 'operating_pressure_bar', 'residence_time_min',
            'media_type', 'resin_age_days', 'elution_ratio', 'feed_temp_process_c',
            
            # Results
            'li_recovery_percent', 'mg_rejection_percent', 'ca_rejection_percent',
            'na_rejection_percent', 'li_product_purity_percent', 'product_grade',
            'mass_balance_error_percent',
            
            # Economic
            'energy_kWh_per_m3', 'chemical_cost_USD_per_m3',
            
            # QA
            'replicate_number', 'rsd_percent', 'outlier_flagged', 
            'mass_balance_valid', 'qc_approved', 'qc_comments',
            'analyst_id', 'lab_id', 'analysis_date', 'data_source', 'provenance',
            
            # Metadata
            '_source_repo', '_source_file', '_source_sheet', '_source_type'
        ]
        
        # Add missing columns
        for col in master_columns:
            if col not in df.columns:
                df[col] = np.nan
        
        # Reorder columns
        df = df[master_columns + [c for c in df.columns if c not in master_columns]]
        
        # Remove rows with no actual data (only metadata)
        data_cols = [c for c in master_columns if not c.startswith('_')]
        df = df[df[data_cols].notna().any(axis=1)]
        
        logger.info(f"✓ Final dataset: {len(df)} rows × {len(df.columns)} columns")
        
        # Step 6: Data quality summary
        logger.info(f"\n{'='*70}")
        logger.info(f"STEP 5: Data Quality Summary")
        logger.info(f"{'='*70}\n")
        
        data_coverage = (1 - df.isna().sum() / len(df)) * 100
        
        key_cols = ['li_ppm', 'li_recovery_percent', 'li_product_purity_percent', 
                    'temperature_c', 'operating_pressure_bar']
        
        for col in key_cols:
            if col in df.columns:
                non_null = df[col].notna().sum()
                coverage = (non_null / len(df)) * 100
                logger.info(f"  {col:30s}: {coverage:6.1f}% ({non_null:5d} values)")
        
        logger.info(f"\n  Data sources (repositories): {df['_source_repo'].nunique()}")
        logger.info(f"  Data file types: {', '.join(df['_source_type'].unique())}")
        
        return df

def main():
    """Main entry point."""
    
    # Initialize scraper
    scraper = GitHubDataScraper()
    
    # Run scraping
    df = scraper.scrape_all(repo_limit=50)
    
    if len(df) == 0:
        logger.error("✗ No data extracted!")
        return
    
    # Save to CSV
    output_path = 'lithium_recovery_aggregated_data.csv'
    df.to_csv(output_path, index=False)
    
    logger.info(f"\n{'='*70}")
    logger.info(f"SUCCESS!")
    logger.info(f"{'='*70}")
    logger.info(f"✓ Data saved to: {output_path}")
    logger.info(f"✓ Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    
    # Display sample
    logger.info(f"\n{'='*70}")
    logger.info(f"Sample Data (first 5 rows):")
    logger.info(f"{'='*70}\n")
    print(df.head())
    
    logger.info(f"\n{'='*70}")
    logger.info(f"Column Info:")
    logger.info(f"{'='*70}\n")
    print(df.info())
    
    logger.info(f"\n{'='*70}")
    logger.info(f"Basic Statistics:")
    logger.info(f"{'='*70}\n")
    print(df.describe())

if __name__ == '__main__':
    main()
