#!/usr/bin/env python3
"""
Behavioral Dashboard Components
Displays behavioral insights in a human-readable, story-like format.
"""

import streamlit as st
import pandas as pd
from typing import Dict, List
import plotly.express as px
import plotly.graph_objects as go

class BehavioralDashboard:
    """Displays behavioral insights in an engaging, story-like format."""
    
    def __init__(self):
        pass
    
    def display_predictive_insights(self, behavioral_insights: Dict):
        """Display predictive insights about upcoming expenses and pattern breaks."""
        st.header("🔮 Predictive Insights")
        
        predictive = behavioral_insights.get('predictive_insights', {})
        
        # Upcoming recurring expenses
        upcoming_expenses = predictive.get('upcoming_expenses', [])
        if upcoming_expenses:
            st.subheader("⏰ Upcoming Big Expenses")
            
            for expense in upcoming_expenses[:3]:  # Show top 3
                days_until = expense.get('days_until_next', 0)
                merchant = expense.get('merchant', 'Unknown')
                amount = expense.get('avg_amount', 0)
                confidence = expense.get('confidence', 'Medium')
                
                if days_until <= 7:
                    st.warning(f"⚠️ **{merchant}**: ₹{amount:,.2f} due in {days_until} days ({confidence} confidence)")
                elif days_until <= 14:
                    st.info(f"📅 **{merchant}**: ₹{amount:,.2f} due in {days_until} days ({confidence} confidence)")
                else:
                    st.success(f"📋 **{merchant}**: ₹{amount:,.2f} due in {days_until} days ({confidence} confidence)")
        else:
            st.info("✅ No upcoming recurring expenses detected")
        
        # Pattern breaks
        pattern_breaks = predictive.get('pattern_breaks', [])
        if pattern_breaks:
            st.subheader("📊 Unusual Spending Patterns")
            
            for break_info in pattern_breaks[:3]:  # Show top 3
                month = break_info.get('month', 'Unknown')
                category = break_info.get('category', 'Unknown')
                deviation = break_info.get('deviation_percent', 0)
                severity = break_info.get('severity', 'Medium')
                
                if severity == 'High':
                    st.error(f"🚨 **{month}**: {category} spending was {deviation:+.1f}% unusual")
                else:
                    st.warning(f"⚠️ **{month}**: {category} spending was {deviation:+.1f}% unusual")
        else:
            st.success("✅ No unusual spending patterns detected")
        
        # Seasonal patterns
        seasonal = predictive.get('seasonal_patterns', {})
        if seasonal:
            st.subheader("📅 Seasonal Patterns")
            
            peak_month = seasonal.get('peak_spending_month', {})
            if peak_month:
                month_name = peak_month.get('month_name', 'Unknown')
                amount = peak_month.get('amount', 0)
                st.info(f"🎯 **Peak spending month**: {month_name} (₹{amount:,.2f})")
            
            weekend_pattern = seasonal.get('weekend_pattern', {})
            if weekend_pattern:
                weekend_ratio = weekend_pattern.get('weekend_ratio', 0)
                if weekend_ratio > 0.4:
                    st.info(f"🎉 **Weekend spender**: {weekend_ratio:.1%} of spending happens on weekends")
                else:
                    st.info(f"💼 **Weekday focused**: {weekend_ratio:.1%} of spending happens on weekends")
    
    def display_personality_profile(self, behavioral_insights: Dict):
        """Display personality traits derived from spending patterns."""
        st.header("👤 Personality Profile")
        
        personality = behavioral_insights.get('personality_profile', {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Digital native level
            digital_info = personality.get('digital_native_level', {})
            digital_ratio = digital_info.get('digital_ratio', 0)
            digital_level = digital_info.get('level', 'Unknown')
            
            st.metric(
                "Digital Native Level",
                digital_level,
                f"{digital_ratio:.1%} digital payments"
            )
        
        with col2:
            # Loyalty index
            loyalty_info = personality.get('loyalty_index', {})
            loyalty_personality = loyalty_info.get('personality', 'Unknown')
            loyalty_ratio = loyalty_info.get('loyalty_ratio', 0)
            
            st.metric(
                "Shopping Style",
                loyalty_personality,
                f"{loyalty_ratio:.1%} loyal merchants"
            )
        
        with col3:
            # Planning style
            planning_info = personality.get('planning_style', {})
            planning_style = planning_info.get('style', 'Unknown')
            planning_ratio = planning_info.get('planning_ratio', 0)
            
            st.metric(
                "Financial Style",
                planning_style,
                f"{planning_ratio:.1%} planned expenses"
            )
        
        # Personality summary
        st.subheader("🎭 Your Financial Personality")
        
        personality_traits = []
        if digital_level == 'High':
            personality_traits.append("**Tech-savvy** - You're comfortable with digital payments")
        if loyalty_personality == 'Loyal':
            personality_traits.append("**Loyal** - You stick to trusted merchants and services")
        elif loyalty_personality == 'Experimental':
            personality_traits.append("**Adventurous** - You love trying new merchants and services")
        if planning_style == 'Planner':
            personality_traits.append("**Organized** - You plan your expenses well")
        elif planning_style == 'Impulsive':
            personality_traits.append("**Spontaneous** - You make decisions on the fly")
        
        if personality_traits:
            for trait in personality_traits:
                st.write(f"• {trait}")
        else:
            st.info("Balanced financial personality - you adapt well to different situations")
    
    def display_lifestyle_patterns(self, behavioral_insights: Dict):
        """Display lifestyle and daily patterns."""
        st.header("🏠 Lifestyle Patterns")
        
        lifestyle = behavioral_insights.get('lifestyle_patterns', {})
        
        # Daily rhythm
        daily_rhythm = lifestyle.get('daily_rhythm', {})
        if daily_rhythm:
            peak_hour = daily_rhythm.get('peak_spending_hour', 0)
            wake_up_time = daily_rhythm.get('financial_wake_up_time', 'Unknown')
            
            st.subheader("⏰ Daily Financial Rhythm")
            st.info(f"**Peak spending hour**: {peak_hour}:00")
            st.info(f"**Financial wake-up time**: {wake_up_time}")
            
            # Create hourly spending chart
            # This would need the actual hourly data from the insights
        
        # Weekend personality
        weekend_personality = lifestyle.get('weekend_personality', {})
        if weekend_personality:
            st.subheader("🎉 Weekend vs Weekday Personality")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Weekend Favorites:**")
                weekend_cats = weekend_personality.get('top_weekend_categories', {})
                for category, amount in list(weekend_cats.items())[:3]:
                    st.write(f"• {category}: ₹{amount:,.2f}")
            
            with col2:
                st.write("**Weekday Favorites:**")
                weekday_cats = weekend_personality.get('top_weekday_categories', {})
                for category, amount in list(weekday_cats.items())[:3]:
                    st.write(f"• {category}: ₹{amount:,.2f}")
        
        # Anchor merchants
        anchor_merchants = lifestyle.get('anchor_merchants', [])
        if anchor_merchants:
            st.subheader("🎯 Your Anchor Merchants")
            st.write("These are the services you use consistently:")
            for merchant in anchor_merchants[:5]:  # Show top 5
                st.write(f"• {merchant}")
        else:
            st.info("No consistent merchant patterns detected")
    
    def display_stress_patterns(self, behavioral_insights: Dict):
        """Display stress-related spending patterns."""
        st.header("😰 Stress & Comfort Patterns")
        
        stress_patterns = behavioral_insights.get('stress_patterns', {})
        
        # Comfort spending
        comfort_spending = stress_patterns.get('comfort_spending', {})
        if comfort_spending:
            st.subheader("🍕 Comfort Spending Categories")
            
            for category, amount in comfort_spending.items():
                st.write(f"• **{category}**: ₹{amount:,.2f}")
        
        # Stress spending days
        stress_days = stress_patterns.get('stress_spending_days', {})
        if stress_days:
            high_freq_days = stress_days.get('high_frequency_days', 0)
            avg_daily = stress_days.get('avg_daily_transactions', 0)
            
            st.subheader("📈 Stress Spending Detection")
            
            if high_freq_days > 0:
                st.warning(f"🚨 **{high_freq_days} high-frequency spending days** detected")
                st.write(f"Average daily transactions: {avg_daily:.1f}")
                st.write("This could indicate stress-related spending patterns")
            else:
                st.success("✅ No stress spending patterns detected")
    
    def display_life_changes(self, behavioral_insights: Dict):
        """Display detected life changes."""
        st.header("🔄 Life Changes Detected")
        
        life_changes = behavioral_insights.get('life_changes', {})
        
        # Income source changes
        income_change = life_changes.get('income_source_change', {})
        if income_change.get('detected', False):
            sources = income_change.get('sources', [])
            st.warning(f"💼 **Job change detected**: Salary source changed from {sources[0]} to {sources[1]}")
        
        # Spending pattern changes
        spending_change = life_changes.get('spending_pattern_change', {})
        if spending_change.get('detected', False):
            change_percent = spending_change.get('change_percent', 0)
            trend = spending_change.get('trend', 'Unknown')
            
            if trend == 'Increasing':
                st.info(f"📈 **Lifestyle upgrade detected**: Spending increased by {change_percent:.1f}%")
            else:
                st.info(f"📉 **Lifestyle change detected**: Spending decreased by {abs(change_percent):.1f}%")
        
        if not income_change.get('detected', False) and not spending_change.get('detected', False):
            st.success("✅ No significant life changes detected")
    
    def display_financial_health_signals(self, behavioral_insights: Dict):
        """Display financial health signals."""
        st.header("💰 Financial Health Signals")
        
        financial_health = behavioral_insights.get('financial_health_signals', {})
        
        # Credit usage patterns
        credit_pattern = financial_health.get('credit_usage_pattern', {})
        if credit_pattern:
            end_month_ratio = credit_pattern.get('end_month_ratio', 0)
            stress_indicator = credit_pattern.get('stress_indicator', False)
            
            st.subheader("💳 Credit Usage Patterns")
            
            if stress_indicator:
                st.error(f"⚠️ **Stress indicator**: {end_month_ratio:.1%} of credit usage is at month-end")
                st.write("This suggests you might be using credit to manage cash flow")
            else:
                st.success(f"✅ **Healthy credit usage**: {end_month_ratio:.1%} of credit usage is at month-end")
        
        # Salary day splurge
        salary_splurge = financial_health.get('salary_day_splurge', {})
        if salary_splurge:
            splurge_ratio = salary_splurge.get('splurge_ratio', 0)
            splurge_amount = salary_splurge.get('splurge_amount', 0)
            
            st.subheader("🎉 Salary Day Behavior")
            
            if splurge_ratio > 0.3:
                st.warning(f"⚠️ **High splurge**: You spend {splurge_ratio:.1%} of salary within 3 days")
                st.write(f"Amount: ₹{splurge_amount:,.2f}")
            else:
                st.success(f"✅ **Disciplined**: You spend {splurge_ratio:.1%} of salary within 3 days")
    
    def display_behavioral_summary(self, behavioral_insights: Dict):
        """Display a comprehensive behavioral summary."""
        st.header("📋 Behavioral Summary")
        
        # Generate a story-like summary
        summary_parts = []
        
        # Personality traits
        personality = behavioral_insights.get('personality_profile', {})
        digital_level = personality.get('digital_native_level', {}).get('level', 'Unknown')
        loyalty_style = personality.get('loyalty_index', {}).get('personality', 'Unknown')
        planning_style = personality.get('planning_style', {}).get('style', 'Unknown')
        
        summary_parts.append(f"You are a **{digital_level.lower()} digital native**")
        summary_parts.append(f"with a **{loyalty_style.lower()} shopping style**")
        summary_parts.append(f"and **{planning_style.lower()} financial approach**")
        
        # Lifestyle patterns
        lifestyle = behavioral_insights.get('lifestyle_patterns', {})
        daily_rhythm = lifestyle.get('daily_rhythm', {})
        wake_up_time = daily_rhythm.get('financial_wake_up_time', 'Unknown')
        
        summary_parts.append(f"Your financial life wakes up **{wake_up_time.lower()}**")
        
        # Stress patterns
        stress_patterns = behavioral_insights.get('stress_patterns', {})
        stress_days = stress_patterns.get('stress_spending_days', {})
        high_freq_days = stress_days.get('high_frequency_days', 0)
        
        if high_freq_days > 0:
            summary_parts.append(f"and you show **stress spending patterns** on {high_freq_days} days")
        
        # Combine into a story
        story = ". ".join(summary_parts) + "."
        
        st.write(story)
        
        # Key insights
        st.subheader("🎯 Key Insights")
        
        insights = []
        
        # Predictive insights
        predictive = behavioral_insights.get('predictive_insights', {})
        upcoming_expenses = predictive.get('upcoming_expenses', [])
        if upcoming_expenses:
            next_expense = upcoming_expenses[0]
            insights.append(f"Next big expense: {next_expense['merchant']} (₹{next_expense['avg_amount']:,.2f})")
        
        # Pattern breaks
        pattern_breaks = predictive.get('pattern_breaks', [])
        if pattern_breaks:
            insights.append(f"Unusual spending detected in {len(pattern_breaks)} categories")
        
        # Life changes
        life_changes = behavioral_insights.get('life_changes', {})
        if life_changes.get('income_source_change', {}).get('detected', False):
            insights.append("Recent job change detected")
        
        for insight in insights:
            st.write(f"• {insight}")
        
        if not insights:
            st.info("No significant behavioral insights to report") 