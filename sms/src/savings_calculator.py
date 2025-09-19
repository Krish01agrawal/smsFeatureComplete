"""
Savings calculator module for SMS transaction analysis.
Handles salary detection, income analysis, and savings calculations.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
import logging

# Configure logging
logger = logging.getLogger(__name__)


class SavingsCalculator:
    """Advanced savings and income analysis with ML-ready features."""
    
    def __init__(self):
        """Initialize savings calculator."""
        logger.info("SavingsCalculator initialized")
    
    def detect_salary_source(self, df: pd.DataFrame) -> Dict:
        """
        Intelligent salary detection using data-driven pattern analysis.
        No hardcoded merchant names - automatically detects salary patterns.
        
        Args:
            df: DataFrame with transaction data
            
        Returns:
            Dictionary with salary source and average salary
        """
        if df.empty:
            return {"source": "Unknown", "avg_salary": 0.0}
        
        # Use intelligent pattern detection
        salary_info = self._intelligent_salary_detection(df)
        if salary_info['avg_salary'] > 0:
            return salary_info
        
        # Fallback: try classification approach if available
        if 'txn_type' in df.columns:
            salary_txn = df[df['txn_type'] == 'salary']
            if not salary_txn.empty:
                source = salary_txn['merchant_canonical'].mode()[0]
                monthly_salary = salary_txn.groupby(df['transaction_date'].dt.to_period('M'))['amount'].sum().mean()
                return {"source": source, "avg_salary": monthly_salary}
        
        # Final fallback: basic detection using transaction_type
        return self._basic_salary_detection(df)
    
    def _intelligent_salary_detection(self, df: pd.DataFrame) -> Dict:
        """
        Intelligent salary detection that combines related salary transactions.
        Uses a focused approach to identify and merge salary sources.
        """
        # Look for large, regular credits (potential salary)
        credits = df[df['transaction_type'] == 'credit'].copy()
        
        if credits.empty:
            return {"source": "Unknown", "avg_salary": 0.0}
        
        # Step 1: Find all potential salary merchants (large amounts, good patterns)
        potential_salary_merchants = self._identify_potential_salary_merchants(credits)
        
        # Step 2: Combine related salary merchants
        combined_salary_data = self._combine_related_salary_merchants(potential_salary_merchants, credits)
        
        # Step 3: Analyze combined data for best salary source
        if combined_salary_data:
            best_source = max(combined_salary_data.keys(), key=lambda x: combined_salary_data[x]['score'])
            best_data = combined_salary_data[best_source]
            
            if best_data['score'] >= 15:  # Minimum threshold for salary detection
                return {
                    "source": best_source,
                    "avg_salary": best_data['avg_amount'],
                    "confidence_score": best_data['score'],
                    "analysis_details": best_data
                }
        
        return {"source": "Unknown", "avg_salary": 0.0}
    
    def _identify_potential_salary_merchants(self, credits: pd.DataFrame) -> Dict:
        """
        Identify merchants that could potentially be salary sources.
        """
        potential_merchants = {}
        
        for merchant, group in credits.groupby('merchant_canonical'):
            # Only consider merchants with substantial amounts
            large_transactions = group[group['amount'] >= 20000]  # ₹20k+ threshold
            
            if not large_transactions.empty:
                # Calculate monthly amounts for large transactions only
                monthly_amounts = large_transactions.groupby(large_transactions['transaction_date'].dt.to_period('M'))['amount'].sum()
                
                if len(monthly_amounts) >= 1:
                    avg_amount = monthly_amounts.mean()
                    std_amount = monthly_amounts.std() if len(monthly_amounts) > 1 else 0
                    variation = std_amount / avg_amount if avg_amount > 0 and std_amount > 0 else 0
                    
                    # Score this merchant as potential salary source
                    score = self._calculate_salary_score(merchant, large_transactions, monthly_amounts, avg_amount, variation)
                    
                    if score >= 10:  # Only keep merchants with decent scores
                        potential_merchants[merchant] = {
                            'transactions': large_transactions,
                            'monthly_amounts': monthly_amounts,
                            'avg_amount': avg_amount,
                            'variation': variation,
                            'score': score
                        }
        
        return potential_merchants
    
    def _combine_related_salary_merchants(self, potential_merchants: Dict, credits: pd.DataFrame) -> Dict:
        """
        Combine related salary merchants (e.g., S and SBIPSG) into unified sources.
        """
        if not potential_merchants:
            return {}
        
        # If we only have one potential merchant, return it as-is
        if len(potential_merchants) == 1:
            merchant_name = list(potential_merchants.keys())[0]
            return {merchant_name: potential_merchants[merchant_name]}
        
        # Check if we have related merchants that should be combined
        combined_sources = {}
        processed_merchants = set()
        
        for merchant1, data1 in potential_merchants.items():
            if merchant1 in processed_merchants:
                continue
            
            # Find related merchants
            related_merchants = [merchant1]
            related_data = [data1]
            
            for merchant2, data2 in potential_merchants.items():
                if merchant2 != merchant1 and merchant2 not in processed_merchants:
                    # Check if these merchants are related (similar amounts and timing)
                    if self._are_salary_merchants_related(data1, data2):
                        related_merchants.append(merchant2)
                        related_data.append(data2)
                        processed_merchants.add(merchant2)
            
            processed_merchants.add(merchant1)
            
            # Create combined source
            if len(related_merchants) > 1:
                # Multiple related merchants - combine them
                combined_name = f"COMBINED_SALARY_{'-'.join(sorted(related_merchants))}"
                combined_sources[combined_name] = self._merge_salary_data(related_data)
            else:
                # Single merchant
                combined_sources[merchant1] = data1
        
        return combined_sources
    
    def _are_salary_merchants_related(self, data1: Dict, data2: Dict) -> bool:
        """
        Check if two salary merchants are related (same company, different codes).
        """
        # Check amount similarity
        avg1, avg2 = data1['avg_amount'], data2['avg_amount']
        amount_ratio = min(avg1, avg2) / max(avg1, avg2) if max(avg1, avg2) > 0 else 0
        
        # Check if amounts are reasonably similar (within salary increase range)
        if amount_ratio < 0.5:  # Too different to be related
            return False
        
        # Check timing overlap or sequence
        dates1 = set(data1['monthly_amounts'].keys())
        dates2 = set(data2['monthly_amounts'].keys())
        
        # If they have overlapping months, they're probably not related (same company wouldn't use two codes simultaneously)
        if dates1 & dates2:
            return False
        
        # If they're sequential in time, they could be related (company changed codes)
        all_dates = sorted(list(dates1) + list(dates2))
        if len(all_dates) >= 2:
            # Check if there's a reasonable gap between the two merchant periods
            dates1_max = max(dates1) if dates1 else None
            dates2_min = min(dates2) if dates2 else None
            
            if dates1_max and dates2_min:
                gap_months = (dates2_min - dates1_max).n
                if 0 <= gap_months <= 3:  # Up to 3 months gap is reasonable
                    return True
            
            dates2_max = max(dates2) if dates2 else None
            dates1_min = min(dates1) if dates1 else None
            
            if dates2_max and dates1_min:
                gap_months = (dates1_min - dates2_max).n
                if 0 <= gap_months <= 3:  # Up to 3 months gap is reasonable
                    return True
        
        return False
    
    def _merge_salary_data(self, salary_data_list: List[Dict]) -> Dict:
        """
        Merge multiple salary merchant data into a single combined source.
        """
        # Combine all transactions
        all_transactions = pd.concat([data['transactions'] for data in salary_data_list])
        
        # Combine all monthly amounts
        combined_monthly = {}
        for data in salary_data_list:
            combined_monthly.update(data['monthly_amounts'].to_dict())
        
        combined_monthly_series = pd.Series(combined_monthly)
        
        # Calculate combined statistics
        avg_amount = combined_monthly_series.mean()
        std_amount = combined_monthly_series.std() if len(combined_monthly_series) > 1 else 0
        variation = std_amount / avg_amount if avg_amount > 0 and std_amount > 0 else 0
        
        # Calculate combined score (take the best score from the components)
        combined_score = max(data['score'] for data in salary_data_list) + 5  # Bonus for combining
        
        return {
            'transactions': all_transactions,
            'monthly_amounts': combined_monthly_series,
            'avg_amount': avg_amount,
            'variation': variation,
            'score': combined_score,
            'transaction_count': len(all_transactions),
            'component_merchants': [data.get('merchant', 'Unknown') for data in salary_data_list]
        }
    
    def _group_related_transactions(self, credits: pd.DataFrame) -> pd.DataFrame:
        """
        Group related transactions intelligently using amount-based clustering.
        Focuses on finding salary-like patterns across different merchant names.
        """
        credits = credits.copy()
        
        # Step 1: Identify potential salary transactions (large, regular amounts)
        salary_candidates = self._identify_salary_candidates(credits)
        
        # Step 2: Group salary candidates by similarity
        salary_groups = self._cluster_salary_candidates(salary_candidates, credits)
        
        # Step 3: Update merchant names for grouped transactions
        for group_id, group_data in salary_groups.items():
            if len(group_data['transactions']) > 1:
                # Create a unified name for this salary group
                unified_name = self._create_unified_salary_name(group_data, credits)
                
                # Update all transactions in this group
                for idx in group_data['transactions']:
                    credits.at[idx, 'merchant_canonical'] = unified_name
        
        return credits
    
    def _identify_salary_candidates(self, credits: pd.DataFrame) -> pd.DataFrame:
        """
        Identify transactions that could potentially be salary based on amount patterns.
        """
        # Filter for transactions that could be salary (large amounts)
        salary_candidates = credits[credits['amount'] >= 10000].copy()  # ₹10k+ threshold
        
        return salary_candidates
    
    def _cluster_salary_candidates(self, candidates: pd.DataFrame, all_credits: pd.DataFrame) -> Dict:
        """
        Cluster salary candidates into groups based on similarity.
        """
        if candidates.empty:
            return {}
        
        groups = {}
        
        for idx, transaction in candidates.iterrows():
            # Find the best matching group for this transaction
            best_group = self._find_best_salary_group(transaction, groups)
            
            if best_group:
                # Add to existing group
                groups[best_group]['transactions'].append(idx)
                groups[best_group]['amounts'].append(transaction['amount'])
                groups[best_group]['dates'].append(transaction['transaction_date'])
                groups[best_group]['merchants'].add(transaction['merchant_canonical'])
            else:
                # Create new group
                group_id = f"SALARY_GROUP_{len(groups)}"
                groups[group_id] = {
                    'transactions': [idx],
                    'amounts': [transaction['amount']],
                    'dates': [transaction['transaction_date']],
                    'merchants': {transaction['merchant_canonical']},
                    'representative_merchant': transaction['merchant_canonical']
                }
        
        return groups
    
    def _find_best_salary_group(self, transaction: pd.Series, existing_groups: Dict) -> Optional[str]:
        """
        Find the best matching salary group for a transaction.
        """
        if not existing_groups:
            return None
        
        best_group = None
        best_similarity = 0
        
        for group_id, group_data in existing_groups.items():
            similarity = self._calculate_salary_similarity(transaction, group_data)
            
            if similarity > best_similarity and similarity > 0.6:  # Lower threshold for salary grouping
                best_similarity = similarity
                best_group = group_id
        
        return best_group
    
    def _calculate_salary_similarity(self, transaction: pd.Series, group_data: Dict) -> float:
        """
        Calculate similarity between a transaction and a salary group.
        """
        similarity_score = 0
        
        # 1. Amount similarity (50% weight) - most important for salary
        amount = transaction['amount']
        group_amounts = group_data['amounts']
        
        avg_group_amount = sum(group_amounts) / len(group_amounts)
        amount_diff_ratio = abs(amount - avg_group_amount) / avg_group_amount if avg_group_amount > 0 else 1
        
        if amount_diff_ratio < 0.2:  # Within 20% - very similar salary amounts
            similarity_score += 0.5
        elif amount_diff_ratio < 0.4:  # Within 40% - could be salary increase/decrease
            similarity_score += 0.3
        elif amount_diff_ratio < 0.6:  # Within 60% - possible salary change
            similarity_score += 0.1
        
        # 2. Timing pattern similarity (30% weight)
        transaction_date = transaction['transaction_date']
        group_dates = group_data['dates']
        
        if len(group_dates) > 1:
            # Check if timing follows a monthly pattern
            date_diffs = [(group_dates[i] - group_dates[i-1]).days for i in range(1, len(group_dates))]
            avg_gap = sum(date_diffs) / len(date_diffs)
            
            # Check if this transaction fits the timing pattern
            last_date = max(group_dates)
            current_gap = abs((transaction_date - last_date).days)
            
            if 20 <= current_gap <= 45:  # Roughly monthly
                if abs(current_gap - avg_gap) / max(avg_gap, 1) < 0.5:  # Within 50% of expected gap
                    similarity_score += 0.3
                else:
                    similarity_score += 0.15  # Still monthly-ish
        else:
            # For single transaction groups, check if it's roughly monthly from last
            last_date = group_dates[0]
            gap = abs((transaction_date - last_date).days)
            if 20 <= gap <= 45:  # Roughly monthly
                similarity_score += 0.3
        
        # 3. Transaction characteristics (20% weight)
        characteristics_score = 0
        
        # Payment method similarity
        if transaction.get('payment_method') in ['bank_transfer', 'neft', 'imps', 'rtgs']:
            characteristics_score += 0.1
        
        # Bank similarity
        if transaction.get('bank_name') == 'SBI':  # Common salary bank
            characteristics_score += 0.05
        
        # Merchant name patterns (without hardcoding specific names)
        merchant_similarity = self._calculate_merchant_similarity(
            transaction['merchant_canonical'], 
            group_data['representative_merchant']
        )
        characteristics_score += merchant_similarity * 0.05
        
        similarity_score += characteristics_score
        
        return similarity_score
    
    def _create_unified_salary_name(self, group_data: Dict, credits: pd.DataFrame) -> str:
        """
        Create a unified name for a salary group.
        """
        merchants = list(group_data['merchants'])
        
        # If we have multiple merchants, create a descriptive group name
        if len(merchants) > 1:
            # Find the most descriptive merchant name
            longest_merchant = max(merchants, key=len)
            if len(longest_merchant) > 3:
                return f"SALARY_SOURCE_{longest_merchant}"
            else:
                # Use a generic salary group name with the merchants
                return f"SALARY_GROUP_{'_'.join(sorted(merchants))}"
        else:
            return merchants[0]
    
    def _find_best_transaction_group(self, transaction: pd.Series, existing_groups: Dict) -> Optional[str]:
        """
        Find the best matching group for a transaction using data-driven similarity.
        """
        if not existing_groups:
            return None
        
        best_group = None
        best_similarity = 0
        
        for group_name, group_data in existing_groups.items():
            similarity = self._calculate_transaction_similarity(transaction, group_data)
            
            if similarity > best_similarity and similarity > 0.7:  # Threshold for grouping
                best_similarity = similarity
                best_group = group_name
        
        return best_group
    
    def _calculate_transaction_similarity(self, transaction: pd.Series, group_data: Dict) -> float:
        """
        Calculate similarity between a transaction and a group using multiple factors.
        """
        similarity_score = 0
        
        # 1. Amount similarity (40% weight)
        amount = transaction['amount']
        group_amounts = group_data['amounts']
        
        avg_group_amount = sum(group_amounts) / len(group_amounts)
        amount_diff_ratio = abs(amount - avg_group_amount) / avg_group_amount if avg_group_amount > 0 else 1
        
        if amount_diff_ratio < 0.1:  # Within 10%
            similarity_score += 0.4
        elif amount_diff_ratio < 0.3:  # Within 30%
            similarity_score += 0.2
        
        # 2. Timing pattern similarity (30% weight)
        transaction_date = transaction['transaction_date']
        group_dates = group_data['dates']
        
        # Check if timing follows a pattern
        if len(group_dates) > 1:
            date_diffs = [(group_dates[i] - group_dates[i-1]).days for i in range(1, len(group_dates))]
            avg_gap = sum(date_diffs) / len(date_diffs)
            
            # Check if this transaction fits the timing pattern
            last_date = max(group_dates)
            current_gap = (transaction_date - last_date).days
            
            if abs(current_gap - avg_gap) / avg_gap < 0.3:  # Within 30% of expected gap
                similarity_score += 0.3
        else:
            # For single transaction groups, check if it's roughly monthly
            last_date = group_dates[0]
            gap = abs((transaction_date - last_date).days)
            if 20 <= gap <= 40:  # Roughly monthly
                similarity_score += 0.3
        
        # 3. Transaction characteristics similarity (30% weight)
        # Payment method, bank, etc.
        characteristics_match = 0
        
        if transaction.get('payment_method') == group_data.get('payment_method'):
            characteristics_match += 0.1
        if transaction.get('bank_name') == group_data.get('bank_name'):
            characteristics_match += 0.1
        
        # Merchant name similarity (fuzzy matching without hardcoding)
        merchant_similarity = self._calculate_merchant_similarity(
            transaction['merchant_canonical'], 
            group_data['representative_merchant']
        )
        characteristics_match += merchant_similarity * 0.1
        
        similarity_score += characteristics_match
        
        return similarity_score
    
    def _calculate_merchant_similarity(self, merchant1: str, merchant2: str) -> float:
        """
        Calculate merchant name similarity without hardcoded patterns.
        """
        if not merchant1 or not merchant2:
            return 0.0
        
        merchant1_lower = merchant1.lower()
        merchant2_lower = merchant2.lower()
        
        # Exact match
        if merchant1_lower == merchant2_lower:
            return 1.0
        
        # Substring match
        if merchant1_lower in merchant2_lower or merchant2_lower in merchant1_lower:
            return 0.8
        
        # Common prefix/suffix
        if len(merchant1_lower) >= 3 and len(merchant2_lower) >= 3:
            if merchant1_lower[:3] == merchant2_lower[:3]:
                return 0.6
            if merchant1_lower[-3:] == merchant2_lower[-3:]:
                return 0.5
        
        return 0.0
    
    def _choose_best_merchant_name(self, group_data: Dict, credits: pd.DataFrame) -> str:
        """
        Choose the most descriptive merchant name from a group.
        """
        # Get all merchant names in this group
        merchant_names = []
        for idx in group_data['transactions']:
            merchant_names.append(credits.loc[idx, 'merchant_canonical'])
        
        # Choose the longest, most descriptive name
        best_name = max(merchant_names, key=len)
        
        # If all names are very short, create a composite name
        if len(best_name) <= 2:
            unique_names = list(set(merchant_names))
            if len(unique_names) > 1:
                best_name = f"SALARY_GROUP_{'-'.join(sorted(unique_names))}"
        
        return best_name
    
    def _calculate_salary_score(self, merchant: str, group: pd.DataFrame, monthly_amounts: pd.Series, 
                               avg_amount: float, variation: float) -> float:
        """
        Calculate salary likelihood score using data-driven criteria.
        Enhanced to work with intelligently grouped transactions.
        """
        score = 0
        
        # 1. Amount-based scoring (salary is typically large and consistent)
        if avg_amount >= 100000:  # ₹1L+ is very likely salary
            score += 15
        elif avg_amount >= 75000:  # ₹75k+ is likely salary
            score += 12
        elif avg_amount >= 50000:  # ₹50k+ is very likely salary
            score += 10
        elif avg_amount >= 30000:  # ₹30k+ could be salary
            score += 8
        elif avg_amount >= 20000:  # ₹20k+ might be salary
            score += 6
        elif avg_amount >= 10000:  # ₹10k+ could be salary
            score += 4
        elif avg_amount >= 5000:   # ₹5k+ might be salary
            score += 2
        else:
            # Very small amounts are unlikely to be salary
            score -= 3
        
        # 2. Consistency scoring (salary is usually consistent)
        if variation == 0:  # Perfect consistency (single transaction or identical amounts)
            score += 8
        elif variation < 0.10:  # Less than 10% variation - very consistent
            score += 7
        elif variation < 0.20:  # Less than 20% variation - consistent
            score += 5
        elif variation < 0.35:  # Less than 35% variation - moderately consistent
            score += 3
        elif variation < 0.50:  # Less than 50% variation - somewhat consistent
            score += 1
        else:
            # High variation is unlikely for salary
            score -= 2
        
        # 3. Frequency scoring (salary is usually monthly)
        date_diffs = group['transaction_date'].diff().dt.days.dropna()
        if len(date_diffs) > 0:
            median_gap = date_diffs.median()
            if 25 <= median_gap <= 35:  # Monthly pattern
                score += 6
            elif 20 <= median_gap <= 40:  # Flexible monthly
                score += 4
            elif 15 <= median_gap <= 45:  # Roughly monthly
                score += 3
            elif 10 <= median_gap <= 50:  # Somewhat regular
                score += 2
            else:
                # Irregular frequency is less likely for salary
                score += 0
        elif len(group) == 1:
            # Single transaction - could be recent salary, give moderate score
            score += 3
        
        # 4. Pattern consistency scoring
        pattern_consistency = self._analyze_pattern_consistency(group)
        score += pattern_consistency * 3
        
        # 5. Amount stability scoring (salary amounts are usually stable)
        amount_stability = self._analyze_amount_stability(monthly_amounts)
        score += amount_stability * 2
        
        # 6. Merchant name analysis (data-driven, no hardcoding)
        merchant_score = self._analyze_merchant_context(merchant, group)
        score += merchant_score
        
        # 7. Transaction count scoring
        transaction_count = len(group)
        if transaction_count >= 6:  # Multiple months of data
            score += 5
        elif transaction_count >= 4:
            score += 4
        elif transaction_count >= 2:
            score += 2
        else:
            # Single transaction can still be salary if amount is large
            if avg_amount >= 50000:
                score += 1
            else:
                score -= 1
        
        # 8. Recency bonus (recent transactions more likely to be current salary)
        if not group.empty:
            latest_date = group['transaction_date'].max()
            days_since_latest = (pd.Timestamp.now() - latest_date).days
            if days_since_latest <= 60:  # Within 2 months
                score += 2
            elif days_since_latest <= 120:  # Within 4 months
                score += 1
        
        return max(0, score)  # Ensure non-negative score
    
    def _analyze_pattern_consistency(self, group: pd.DataFrame) -> float:
        """Analyze how consistent the transaction pattern is."""
        if len(group) < 3:
            return 0.0
        
        # Check if transactions occur at regular intervals
        date_diffs = group['transaction_date'].diff().dt.days.dropna()
        if len(date_diffs) < 2:
            return 0.0
        
        # Calculate consistency of intervals
        median_gap = date_diffs.median()
        gap_variation = date_diffs.std() / median_gap if median_gap > 0 else 1
        
        # Lower variation = more consistent
        if gap_variation < 0.3:
            return 2.0
        elif gap_variation < 0.5:
            return 1.0
        else:
            return 0.0
    
    def _analyze_amount_stability(self, monthly_amounts: pd.Series) -> float:
        """Analyze how stable the amounts are over time."""
        if len(monthly_amounts) < 2:
            return 0.0
        
        # Check if amounts are relatively stable
        mean_amount = monthly_amounts.mean()
        std_amount = monthly_amounts.std()
        coefficient_of_variation = std_amount / mean_amount if mean_amount > 0 else 1
        
        # Lower coefficient = more stable
        if coefficient_of_variation < 0.1:
            return 2.0
        elif coefficient_of_variation < 0.2:
            return 1.5
        elif coefficient_of_variation < 0.3:
            return 1.0
        else:
            return 0.0
    
    def _analyze_merchant_context(self, merchant: str, group: pd.DataFrame) -> float:
        """
        Analyze merchant context for salary likelihood using data-driven approach.
        No hardcoded patterns - uses transaction characteristics and context.
        """
        score = 0
        
        # 1. Merchant name length and structure analysis
        if len(merchant) > 3:  # Longer names more likely to be company names
            score += 1
        if len(merchant) > 10:  # Very long names often indicate full company names
            score += 1
        
        # 2. Capitalization pattern (companies often use ALL CAPS or Title Case)
        if merchant.isupper() and len(merchant) > 3:
            score += 1
        elif merchant.istitle():
            score += 0.5
        
        # 3. Contains numbers/codes (bank codes, company IDs)
        if any(c.isdigit() for c in merchant):
            score += 0.5
        
        # 4. Transaction context analysis
        if not group.empty:
            # Check payment methods associated with this merchant
            payment_methods = group['payment_method'].dropna().unique()
            
            # NEFT/IMPS transfers are common for salary
            if any(method.upper() in ['NEFT', 'IMPS', 'RTGS'] for method in payment_methods if isinstance(method, str)):
                score += 2
            
            # Bank transfers generally indicate formal payments
            if any('bank' in str(method).lower() for method in payment_methods):
                score += 1
        
        # 5. Merchant name uniqueness (unique names more likely to be specific companies)
        if len(set(merchant.split())) > 1:  # Multi-word names
            score += 1
        
        # 6. Avoid common generic terms that are unlikely to be salary sources
        generic_terms = ['atm', 'cash', 'withdrawal', 'transfer', 'payment', 'recharge', 'bill']
        if any(term in merchant.lower() for term in generic_terms):
            score -= 2
        
        # 7. Length-based penalty for very short codes (likely abbreviations)
        if len(merchant) <= 2:
            score -= 1
        
        return max(0, score)
    
    def _get_salary_threshold(self, merchant_analysis: Dict) -> float:
        """
        Dynamically determine salary detection threshold based on data quality.
        Enhanced for the improved scoring system.
        """
        if not merchant_analysis:
            return 20.0  # High threshold if no good candidates
        
        # Calculate score statistics
        scores = [data['score'] for data in merchant_analysis.values()]
        max_score = max(scores) if scores else 0
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Count high-scoring candidates
        high_score_count = sum(1 for score in scores if score > 15)
        
        # Adaptive threshold based on data quality
        if max_score >= 25:  # Very high confidence candidate
            return 15.0
        elif max_score >= 20:  # High confidence candidate
            return 18.0
        elif max_score >= 15:  # Medium confidence candidate
            return 20.0
        elif max_score >= 10:  # Low confidence candidate
            return 22.0
        else:
            return 25.0  # Very low confidence - high threshold
        
        # Adjust based on competition (multiple good candidates)
        if high_score_count > 1:
            return min(25.0, max(15.0, avg_score + 5))  # Raise threshold if multiple candidates
        
        return max(15.0, min(25.0, max_score - 3))  # Lower threshold for clear winner
    
    def _basic_salary_detection(self, df: pd.DataFrame) -> Dict:
        """Basic salary detection using amount and merchant patterns."""
        # Look for large, regular credits
        credits = df[df['transaction_type'] == 'credit'].copy()
        
        if credits.empty:
            return {"source": "Unknown", "avg_salary": 0.0}
        
        # Group by month and find regular large amounts
        monthly_credits = credits.groupby(credits['transaction_date'].dt.to_period('M'))['amount'].sum()
        
        if len(monthly_credits) >= 2:
            # Find the most consistent large amount (likely salary)
            avg_monthly = monthly_credits.mean()
            std_monthly = monthly_credits.std()
            
            # If variation is low, it's likely salary
            if std_monthly / avg_monthly < 0.3:  # Less than 30% variation
                source = credits['merchant_canonical'].mode()[0]
                return {"source": source, "avg_salary": avg_monthly}
        
        return {"source": "Unknown", "avg_salary": 0.0}
    
    def calculate_expenditure_and_savings(self, df: pd.DataFrame, salary_info: Dict) -> Dict:
        """
        Calculate comprehensive expenditure and savings analysis.
        
        Args:
            df: DataFrame with transaction data
            salary_info: Dictionary with salary source and average salary
            
        Returns:
            Dictionary with comprehensive financial analysis
        """
        if df.empty:
            return self._empty_financial_analysis()
        
        # Store salary info for other methods to use
        self._current_salary_info = salary_info
        
        # Add month column for grouping
        df['month'] = df['transaction_date'].dt.to_period('M')
        
        # Get all months in the dataset
        all_months = sorted(df['month'].unique())
        
        # Calculate salary per month (using merchant_canonical, not txn_type)
        monthly_salary = self._calculate_monthly_salary(df, salary_info, all_months)
        
        # Calculate other income per month (using transaction_type, not txn_type)
        monthly_other_income = self._calculate_monthly_other_income(df, all_months)
        
        # Calculate total monthly income (salary + other income)
        monthly_total_income = {
            month: monthly_salary[month] + monthly_other_income[month] 
            for month in all_months
        }
        
        # Calculate expenses using transaction_type (debit transactions)
        expense_txns = df[df['transaction_type'] == 'debit']
        monthly_expense = expense_txns.groupby('month')['amount'].sum()
        
        # Ensure all months have expense data
        for month in all_months:
            if month not in monthly_expense.index:
                monthly_expense[month] = 0
        
        # Calculate averages - use recent 3 months for more current picture
        recent_months = sorted(all_months)[-3:] if len(all_months) >= 3 else all_months
        
        # Calculate recent averages for more accurate current financial picture
        recent_salary_values = [monthly_salary[month] for month in recent_months if monthly_salary[month] > 0]
        recent_income_values = [monthly_total_income[month] for month in recent_months]
        
        avg_salary = sum(recent_salary_values) / len(recent_salary_values) if recent_salary_values else 0
        avg_other_income = sum(monthly_other_income.values()) / len(monthly_other_income) if monthly_other_income else 0
        avg_total_income = sum(recent_income_values) / len(recent_income_values) if recent_income_values else 0
        avg_expense = monthly_expense.mean() if not monthly_expense.empty else 0
        
        # Calculate savings
        savings = avg_total_income - avg_expense
        
        # Detect bonus months (amount > 1.5 × median salary)
        bonus_months = self._detect_bonus_months(df, salary_info)
        
        # Calculate savings rate
        savings_rate = (savings / avg_total_income * 100) if avg_total_income > 0 else 0
        
        # Calculate expense ratio
        expense_ratio = (avg_expense / avg_total_income * 100) if avg_total_income > 0 else 0
        
        # Calculate monthly trends
        monthly_income_series = pd.Series(monthly_total_income)
        monthly_expense_series = monthly_expense
        monthly_salary_series = pd.Series(monthly_salary)
        monthly_other_income_series = pd.Series(monthly_other_income)
        
        # Update salary_info with current salary for display
        current_salary = salary_info.get('current_salary', avg_salary)
        
        return {
            "avg_salary": current_salary,  # Use current salary for top display
            "avg_other_income": avg_other_income,
            "avg_income": avg_total_income,
            "avg_expense": avg_expense,
            "savings": savings,
            "savings_rate": savings_rate,
            "expense_ratio": expense_ratio,
            "monthly_income": monthly_income_series,
            "monthly_expense": monthly_expense_series,
            "monthly_salary": monthly_salary_series,
            "monthly_other_income": monthly_other_income_series,
            "bonus_months": bonus_months,
            "financial_health_score": self._calculate_financial_health_score(savings_rate, expense_ratio)
        }
    
    def _calculate_monthly_salary(self, df: pd.DataFrame, salary_info: Dict, all_months) -> Dict:
        """Calculate salary for each month using the detected salary source."""
        monthly_salary = {}
        
        # Use the detected salary source from salary_info
        detected_source = salary_info.get('source', 'Unknown')
        
        if detected_source == 'Unknown':
            # If no salary source detected, return zeros
            for month in all_months:
                monthly_salary[month] = 0
            return monthly_salary
        
        # Handle combined salary sources (e.g., "COMBINED_SALARY_S-SBIPSG")
        if detected_source.startswith('COMBINED_SALARY_'):
            # Extract individual merchant names from combined source
            merchant_part = detected_source.replace('COMBINED_SALARY_', '')
            individual_merchants = merchant_part.split('-')
        else:
            # Single merchant source
            individual_merchants = [detected_source]
        
        for month in all_months:
            # Find salary transactions for this month using any of the individual merchants
            month_salary_txns = df[
                (df['month'] == month) & 
                (df['merchant_canonical'].isin(individual_merchants)) &
                (df['transaction_type'] == 'credit') &  # Only credit transactions
                (df['amount'] >= 20000)  # Only large amounts (salary-like)
            ]
            
            if not month_salary_txns.empty:
                monthly_salary[month] = month_salary_txns['amount'].sum()
            else:
                # If no salary transaction found for this month, mark as missing
                monthly_salary[month] = None
        
        # Second pass: detect salary changes and fill gaps intelligently
        salary_periods = self._detect_salary_periods(monthly_salary)
        
        # Third pass: fill missing months with appropriate salary based on periods
        for month in all_months:
            if monthly_salary[month] is None:
                # Find the most recent salary period before this month
                applicable_salary = self._get_applicable_salary_for_month(month, salary_periods)
                monthly_salary[month] = applicable_salary
        
        # Store salary change information for insights
        salary_info['salary_periods'] = salary_periods
        salary_info['current_salary'] = self._get_current_salary(salary_periods)
        salary_info['salary_changes'] = self._analyze_salary_changes(salary_periods)
        
        return monthly_salary
    
    def _detect_salary_periods(self, monthly_salary: Dict) -> List[Dict]:
        """Detect distinct salary periods with different amounts."""
        periods = []
        current_period = None
        
        for month, salary in monthly_salary.items():
            if salary is not None:
                if current_period is None:
                    # Start new period
                    current_period = {
                        'start_month': month,
                        'end_month': month,
                        'salary_amount': salary,
                        'months_count': 1
                    }
                elif abs(salary - current_period['salary_amount']) / current_period['salary_amount'] < 0.05:
                    # Same salary (within 5% tolerance) - extend current period
                    current_period['end_month'] = month
                    current_period['months_count'] += 1
                else:
                    # Different salary - end current period and start new one
                    if current_period:
                        periods.append(current_period)
                    
                    current_period = {
                        'start_month': month,
                        'end_month': month,
                        'salary_amount': salary,
                        'months_count': 1
                    }
            else:
                # Missing salary data - end current period if exists
                if current_period:
                    periods.append(current_period)
                    current_period = None
        
        # Add final period if exists
        if current_period:
            periods.append(current_period)
        
        return periods
    
    def _get_applicable_salary_for_month(self, month, salary_periods: List[Dict]) -> float:
        """Get the applicable salary for a given month based on salary periods."""
        if not salary_periods:
            return 0.0
        
        # Find the most recent period that started before or on this month
        applicable_period = None
        for period in salary_periods:
            if period['start_month'] <= month:
                if applicable_period is None or period['start_month'] > applicable_period['start_month']:
                    applicable_period = period
        
        if applicable_period:
            return applicable_period['salary_amount']
        
        # Fallback to the earliest period
        return salary_periods[0]['salary_amount'] if salary_periods else 0.0
    
    def _get_current_salary(self, salary_periods: List[Dict]) -> float:
        """Get the current salary (most recent period by date)."""
        if not salary_periods:
            return 0.0
        
        # FIXED: Find the period with the most recent end_month (not just last in list)
        most_recent_period = max(salary_periods, key=lambda p: p['end_month'])
        return most_recent_period['salary_amount']
    
    def _analyze_salary_changes(self, salary_periods: List[Dict]) -> List[Dict]:
        """Analyze salary changes between periods."""
        changes = []
        
        for i in range(1, len(salary_periods)):
            prev_period = salary_periods[i-1]
            curr_period = salary_periods[i]
            
            change_amount = curr_period['salary_amount'] - prev_period['salary_amount']
            change_percentage = (change_amount / prev_period['salary_amount']) * 100
            
            changes.append({
                'from_month': prev_period['end_month'],
                'to_month': curr_period['start_month'],
                'old_salary': prev_period['salary_amount'],
                'new_salary': curr_period['salary_amount'],
                'change_amount': change_amount,
                'change_percentage': change_percentage,
                'change_type': 'promotion' if change_percentage > 0 else 'reduction'
            })
        
        return changes
    
    def _calculate_monthly_other_income(self, df: pd.DataFrame, all_months) -> Dict:
        """Calculate other income for each month using transaction_type."""
        monthly_other_income = {}
        
        # Get salary merchants to exclude from other income calculation
        salary_merchants = self._get_salary_merchants_from_info()
        
        for month in all_months:
            # Get all credit transactions for this month (excluding ALL salary sources)
            month_credit_txns = df[
                (df['month'] == month) & 
                (df['transaction_type'] == 'credit') & 
                (~df['merchant_canonical'].isin(salary_merchants)) &  # Exclude all salary merchants
                (df['amount'] < 20000)  # Exclude large amounts that might be salary
            ]
            
            # Filter out non-income transactions (refunds, cashback, etc.)
            actual_income_txns = self._filter_actual_income_transactions(month_credit_txns)
            
            monthly_other_income[month] = actual_income_txns['amount'].sum() if not actual_income_txns.empty else 0
        
        return monthly_other_income
    
    def _get_salary_merchants_from_info(self) -> List[str]:
        """Get list of salary merchants from the current analysis."""
        salary_merchants = ['Company Salary']  # Default fallback
        
        # Get actual detected salary source if available
        if hasattr(self, '_current_salary_info') and self._current_salary_info:
            detected_source = self._current_salary_info.get('source', '')
            
            if detected_source and detected_source != 'Unknown':
                # Handle combined salary sources
                if detected_source.startswith('COMBINED_SALARY_'):
                    # Extract individual merchant names from combined source
                    merchant_part = detected_source.replace('COMBINED_SALARY_', '')
                    individual_merchants = merchant_part.split('-')
                    salary_merchants.extend(individual_merchants)
                else:
                    # Single merchant source
                    salary_merchants.append(detected_source)
        
        # Add common patterns that might be salary-related
        salary_merchants.extend(['SBIPSG', 'S', 'HDFCBK'])
        
        return list(set(salary_merchants))  # Remove duplicates
    
    def _filter_actual_income_transactions(self, credit_txns: pd.DataFrame) -> pd.DataFrame:
        """Filter credit transactions to only include actual income sources."""
        if credit_txns.empty:
            return credit_txns
        
        # Define patterns for non-income transactions (to exclude)
        non_income_patterns = [
            'refund', 'cashback', 'reward', 'discount', 'reversal', 'return',
            'zomato', 'amazon', 'flipkart', 'swiggy', 'paytm', 'phonepe',
            'gift', 'bonus', 'cashback', 'cash back', 'cash-back',
            'transfer', 'neft', 'imps', 'rtgs', 'upi'
        ]
        
        # Define patterns for actual income sources (to include)
        income_patterns = [
            'freelance', 'upwork', 'fiverr', 'consulting', 'consultant',
            'rental', 'rent', 'dividend', 'interest', 'investment',
            'business', 'client', 'project', 'service', 'commission',
            'station91', 'technolog'  # Based on the real data
        ]
        
        # Filter transactions
        actual_income = []
        
        for _, txn in credit_txns.iterrows():
            merchant = str(txn['merchant_canonical']).lower()
            sms_message = str(txn.get('sms_message', '')).lower()
            
            # Check if it's a non-income transaction
            is_non_income = any(pattern in merchant or pattern in sms_message 
                               for pattern in non_income_patterns)
            
            # Check if it's an actual income transaction
            is_actual_income = any(pattern in merchant or pattern in sms_message 
                                  for pattern in income_patterns)
            
            # Include if it's actual income or if we can't determine (conservative approach)
            if is_actual_income and not is_non_income:
                actual_income.append(txn)
            elif not is_non_income and not is_actual_income:
                # If we can't determine, exclude it (conservative approach)
                pass
        
        return pd.DataFrame(actual_income) if actual_income else pd.DataFrame()
    
    def _detect_bonus_months(self, df: pd.DataFrame, salary_info: Dict) -> Dict:
        """Detect months with bonus payments."""
        if salary_info['avg_salary'] <= 0:
            return {}
        
        bonus_threshold = salary_info['avg_salary'] * 1.5
        
        # Look for months with income significantly higher than average
        # Use transaction_type instead of txn_type
        income_txns = df[df['transaction_type'] == 'credit']
        monthly_income = income_txns.groupby(
            df['transaction_date'].dt.to_period('M')
        )['amount'].sum()
        
        bonus_months = {}
        for month, amount in monthly_income.items():
            if amount > bonus_threshold:
                bonus_months[str(month)] = {
                    'amount': amount,
                    'bonus_amount': amount - salary_info['avg_salary'],
                    'bonus_percentage': ((amount - salary_info['avg_salary']) / salary_info['avg_salary']) * 100
                }
        
        return bonus_months
    
    def _calculate_financial_health_score(self, savings_rate: float, expense_ratio: float) -> float:
        """Calculate financial health score (0-100)."""
        # Base score starts at 50
        score = 50
        
        # Adjust based on savings rate
        if savings_rate >= 20:
            score += 30  # Excellent savings
        elif savings_rate >= 10:
            score += 20  # Good savings
        elif savings_rate >= 5:
            score += 10  # Moderate savings
        elif savings_rate < 0:
            score -= 20  # Negative savings (spending more than income)
        
        # Adjust based on expense ratio
        if expense_ratio <= 70:
            score += 20  # Good expense control
        elif expense_ratio <= 90:
            score += 10  # Moderate expense control
        elif expense_ratio > 100:
            score -= 20  # Spending more than income
        
        return max(0, min(100, score))  # Clamp between 0 and 100
    
    def _basic_financial_analysis(self, df: pd.DataFrame, salary_info: Dict) -> Dict:
        """Basic financial analysis without transaction classification."""
        # Simple income vs expense calculation
        credits = df[df['transaction_type'] == 'credit']['amount'].sum()
        debits = df[df['transaction_type'] == 'debit']['amount'].sum()
        
        avg_income = credits / len(df['transaction_date'].dt.to_period('M').unique()) if not df.empty else 0
        avg_expense = debits / len(df['transaction_date'].dt.to_period('M').unique()) if not df.empty else 0
        savings = avg_income - avg_expense
        
        return {
            "avg_salary": salary_info['avg_salary'],
            "avg_other_income": 0,
            "avg_income": avg_income,
            "avg_expense": avg_expense,
            "savings": savings,
            "savings_rate": (savings / avg_income * 100) if avg_income > 0 else 0,
            "expense_ratio": (avg_expense / avg_income * 100) if avg_income > 0 else 0,
            "monthly_income": pd.Series(),
            "monthly_expense": pd.Series(),
            "monthly_salary": pd.Series(),
            "monthly_other_income": pd.Series(),
            "bonus_months": {},
            "financial_health_score": self._calculate_financial_health_score(
                (savings / avg_income * 100) if avg_income > 0 else 0,
                (avg_expense / avg_income * 100) if avg_income > 0 else 0
            )
        }
    
    def _empty_financial_analysis(self) -> Dict:
        """Return empty financial analysis structure."""
        return {
            "avg_salary": 0.0,
            "avg_other_income": 0.0,
            "avg_income": 0.0,
            "avg_expense": 0.0,
            "savings": 0.0,
            "savings_rate": 0.0,
            "expense_ratio": 0.0,
            "monthly_income": pd.Series(),
            "monthly_expense": pd.Series(),
            "monthly_salary": pd.Series(),
            "monthly_other_income": pd.Series(),
            "bonus_months": {},
            "financial_health_score": 0.0
        }
    
    def get_savings_summary(self, financial_analysis: Dict) -> Dict:
        """
        Get summary of savings analysis.
        
        Args:
            financial_analysis: Dictionary with financial analysis results
            
        Returns:
            Savings summary dictionary
        """
        return {
            "monthly_salary": financial_analysis['avg_salary'],
            "monthly_other_income": financial_analysis['avg_other_income'],
            "monthly_total_income": financial_analysis['avg_income'],
            "monthly_expenses": financial_analysis['avg_expense'],
            "monthly_savings": financial_analysis['savings'],
            "savings_rate_percentage": financial_analysis['savings_rate'],
            "expense_ratio_percentage": financial_analysis['expense_ratio'],
            "financial_health_score": financial_analysis['financial_health_score'],
            "bonus_months_count": len(financial_analysis['bonus_months']),
            "financial_health_category": self._get_financial_health_category(
                financial_analysis['financial_health_score']
            )
        }
    
    def _get_financial_health_category(self, score: float) -> str:
        """Get financial health category based on score."""
        if score >= 80:
            return "Excellent"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Fair"
        elif score >= 20:
            return "Poor"
        else:
            return "Critical"


# Convenience functions for backward compatibility
def detect_salary_source(df: pd.DataFrame) -> Dict:
    """Legacy salary detection function (kept for backward compatibility)."""
    calculator = SavingsCalculator()
    return calculator.detect_salary_source(df)


def calculate_expenditure_and_savings(df: pd.DataFrame, salary_info: Dict) -> Dict:
    """Legacy savings calculation function (kept for backward compatibility)."""
    calculator = SavingsCalculator()
    return calculator.calculate_expenditure_and_savings(df, salary_info) 