#!/usr/bin/env python3
"""
Optimized Dashboard Components
Provides enhanced UI components with better UX and performance.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional, Callable
import asyncio
from datetime import datetime, timedelta
import time

class DashboardComponents:
    """Optimized dashboard components with enhanced UX."""
    
    def __init__(self):
        self.session_state = st.session_state
        
    def show_loading_state(self, message: str = "Analyzing your data..."):
        """Show an engaging loading state with progress."""
        with st.spinner(message):
            # Create a progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Simulate progress updates
            for i in range(101):
                time.sleep(0.02)
                progress_bar.progress(i)
                if i < 30:
                    status_text.text("🔄 Loading transaction data...")
                elif i < 60:
                    status_text.text("🧠 Analyzing spending patterns...")
                elif i < 80:
                    status_text.text("🔮 Generating behavioral insights...")
                else:
                    status_text.text("✨ Finalizing your personalized dashboard...")
            
            progress_bar.empty()
            status_text.empty()
    
    def show_welcome_screen(self):
        """Show an engaging welcome screen."""
        st.markdown("""
        # 🎉 Welcome to Your Financial Intelligence Dashboard!
        
        ### Discover the Hidden Patterns in Your Financial Life
        
        This AI-powered dashboard will reveal:
        - 🧠 **Your Financial Personality** - Are you a planner or spontaneous spender?
        - 🔮 **Predictive Insights** - Know what's coming before it happens
        - 😰 **Stress Patterns** - Understand your emotional spending triggers
        - 🏠 **Lifestyle Analysis** - See how your daily habits affect your finances
        - 💰 **Financial Health Score** - Get a complete picture of your money habits
        
        ---
        """)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("📊 **Smart Analytics**\n\nAdvanced pattern recognition to understand your spending behavior")
        
        with col2:
            st.success("🔮 **Predictive Power**\n\nForecast upcoming expenses and identify potential issues")
        
        with col3:
            st.warning("🎯 **Actionable Insights**\n\nGet personalized recommendations to improve your financial health")
    
    def show_quick_stats_cards(self, insights: Dict):
        """Show quick stats in an engaging card layout."""
        st.subheader("📊 Your Financial Snapshot")
        
        # Create animated metric cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            self._metric_card(
                "💰 Total Income",
                f"₹{insights.get('avg_income', 0):,.0f}",
                "monthly",
                "trending_up"
            )
        
        with col2:
            self._metric_card(
                "💸 Total Expenses",
                f"₹{insights.get('avg_expense', 0):,.0f}",
                "monthly",
                "trending_down"
            )
        
        with col3:
            savings = insights.get('savings', 0)
            savings_rate = insights.get('savings_rate', 0)
            self._metric_card(
                "💎 Savings",
                f"₹{savings:,.0f}",
                f"{savings_rate:.1f}% of income",
                "savings" if savings > 0 else "warning"
            )
        
        with col4:
            health_score = insights.get('financial_health_score', 0)
            self._metric_card(
                "🏥 Health Score",
                f"{health_score}/100",
                self._get_health_status(health_score),
                "favorite" if health_score > 70 else "warning"
            )
    
    def _metric_card(self, title: str, value: str, subtitle: str, icon: str):
        """Create an engaging metric card."""
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1rem;
            border-radius: 10px;
            color: white;
            text-align: center;
            margin: 0.5rem 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        ">
            <h3 style="margin: 0; font-size: 0.9rem; opacity: 0.9;">{title}</h3>
            <h2 style="margin: 0.5rem 0; font-size: 1.5rem; font-weight: bold;">{value}</h2>
            <p style="margin: 0; font-size: 0.8rem; opacity: 0.8;">{subtitle}</p>
        </div>
        """, unsafe_allow_html=True)
    
    def _get_health_status(self, score: float) -> str:
        """Get health status based on score."""
        if score >= 80:
            return "Excellent"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Fair"
        else:
            return "Needs Attention"
    
    def show_behavioral_insights_carousel(self, behavioral_insights: Dict):
        """Show behavioral insights in an engaging carousel format."""
        st.subheader("🧠 Your Financial Personality")
        
        # Create tabs for different insights
        tab1, tab2, tab3, tab4 = st.tabs(["🎭 Personality", "🔮 Predictions", "😰 Stress Patterns", "🏠 Lifestyle"])
        
        with tab1:
            self._show_personality_insights(behavioral_insights)
        
        with tab2:
            self._show_predictive_insights(behavioral_insights)
        
        with tab3:
            self._show_stress_patterns(behavioral_insights)
        
        with tab4:
            self._show_lifestyle_insights(behavioral_insights)
    
    def _show_personality_insights(self, behavioral_insights: Dict):
        """Show personality insights in an engaging way."""
        personality = behavioral_insights.get('personality_profile', {})
        
        # Digital native level
        digital_info = personality.get('digital_native_level', {})
        digital_level = digital_info.get('level', 'Unknown')
        digital_ratio = digital_info.get('digital_ratio', 0)
        
        st.markdown(f"""
        ### 🚀 Digital Native Level: **{digital_level}**
        
        You use digital payments for **{digital_ratio:.1%}** of your transactions.
        
        {self._get_digital_native_description(digital_level)}
        """)
        
        # Shopping style
        loyalty_info = personality.get('loyalty_index', {})
        loyalty_personality = loyalty_info.get('personality', 'Unknown')
        
        st.markdown(f"""
        ### 🛒 Shopping Style: **{loyalty_personality}**
        
        You prefer to stick with trusted merchants and services.
        """)
        
        # Financial style
        planning_info = personality.get('planning_style', {})
        planning_style = planning_info.get('style', 'Unknown')
        
        st.markdown(f"""
        ### 💡 Financial Approach: **{planning_style}**
        
        {self._get_planning_style_description(planning_style)}
        """)
    
    def _get_digital_native_description(self, level: str) -> str:
        """Get description for digital native level."""
        descriptions = {
            'High': "🎯 You're a tech-savvy digital native who embraces new payment technologies!",
            'Medium': "📱 You're comfortable with digital payments but still use traditional methods sometimes.",
            'Low': "💳 You prefer traditional payment methods and are cautious about digital payments."
        }
        return descriptions.get(level, "Digital payment patterns analyzed.")
    
    def _get_planning_style_description(self, style: str) -> str:
        """Get description for planning style."""
        descriptions = {
            'Planner': "📋 You're organized and plan your expenses well. Great financial discipline!",
            'Impulsive': "⚡ You make spontaneous decisions and enjoy the thrill of impulse purchases.",
            'Balanced': "⚖️ You have a good balance between planning and flexibility."
        }
        return descriptions.get(style, "Financial planning patterns analyzed.")
    
    def _show_predictive_insights(self, behavioral_insights: Dict):
        """Show predictive insights in an engaging way."""
        predictive = behavioral_insights.get('predictive_insights', {})
        
        # Upcoming expenses
        upcoming_expenses = predictive.get('upcoming_expenses', [])
        if upcoming_expenses:
            st.markdown("### ⏰ Upcoming Big Expenses")
            
            for i, expense in enumerate(upcoming_expenses[:3]):
                days_until = expense.get('days_until_next', 0)
                merchant = expense.get('merchant', 'Unknown')
                amount = expense.get('avg_amount', 0)
                
                if days_until <= 7:
                    st.error(f"🚨 **{merchant}**: ₹{amount:,.2f} due in {days_until} days")
                elif days_until <= 14:
                    st.warning(f"⚠️ **{merchant}**: ₹{amount:,.2f} due in {days_until} days")
                else:
                    st.info(f"📅 **{merchant}**: ₹{amount:,.2f} due in {days_until} days")
        else:
            st.success("✅ No upcoming recurring expenses detected")
        
        # Pattern breaks
        pattern_breaks = predictive.get('pattern_breaks', [])
        if pattern_breaks:
            st.markdown("### 📊 Unusual Spending Patterns")
            
            for break_info in pattern_breaks[:2]:
                month = break_info.get('month', 'Unknown')
                category = break_info.get('category', 'Unknown')
                deviation = break_info.get('deviation_percent', 0)
                
                st.warning(f"🚨 **{month}**: {category} spending was {deviation:+.1f}% unusual")
    
    def _show_stress_patterns(self, behavioral_insights: Dict):
        """Show stress patterns in an engaging way."""
        stress_patterns = behavioral_insights.get('stress_patterns', {})
        
        # Comfort spending
        comfort_spending = stress_patterns.get('comfort_spending', {})
        if comfort_spending:
            st.markdown("### 🍕 Your Comfort Spending Categories")
            
            for category, amount in comfort_spending.items():
                st.write(f"• **{category}**: ₹{amount:,.2f}")
        
        # Stress spending days
        stress_days = stress_patterns.get('stress_spending_days', {})
        if stress_days:
            high_freq_days = stress_days.get('high_frequency_days', 0)
            
            if high_freq_days > 0:
                st.warning(f"🚨 **{high_freq_days} high-frequency spending days** detected")
                st.write("This could indicate stress-related spending patterns. Consider tracking your mood when making purchases.")
            else:
                st.success("✅ No stress spending patterns detected")
    
    def _show_lifestyle_insights(self, behavioral_insights: Dict):
        """Show lifestyle insights in an engaging way."""
        lifestyle = behavioral_insights.get('lifestyle_patterns', {})
        
        # Daily rhythm
        daily_rhythm = lifestyle.get('daily_rhythm', {})
        if daily_rhythm:
            peak_hour = daily_rhythm.get('peak_spending_hour', 0)
            wake_up_time = daily_rhythm.get('financial_wake_up_time', 'Unknown')
            
            st.markdown(f"""
            ### ⏰ Your Daily Financial Rhythm
            
            **Peak spending hour**: {peak_hour}:00
            **Financial wake-up time**: {wake_up_time}
            """)
        
        # Anchor merchants
        anchor_merchants = lifestyle.get('anchor_merchants', [])
        if anchor_merchants:
            st.markdown("### 🎯 Your Anchor Merchants")
            st.write("These are the services you use consistently:")
            
            for merchant in anchor_merchants[:5]:
                st.write(f"• {merchant}")
    
    def show_interactive_charts(self, insights: Dict):
        """Show interactive charts with enhanced UX."""
        st.subheader("📈 Interactive Financial Charts")
        
        # Create tabs for different chart types
        tab1, tab2, tab3 = st.tabs(["💰 Spending Trends", "📊 Category Analysis", "⏰ Time Patterns"])
        
        with tab1:
            self._show_spending_trends_chart(insights)
        
        with tab2:
            self._show_category_analysis_chart(insights)
        
        with tab3:
            self._show_time_patterns_chart(insights)
    
    def _show_spending_trends_chart(self, insights: Dict):
        """Show spending trends chart."""
        monthly_expense = insights.get('monthly_expense', pd.Series())
        
        if not monthly_expense.empty:
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=[str(month) for month in monthly_expense.index],
                y=monthly_expense.values,
                mode='lines+markers',
                name='Monthly Expenses',
                line=dict(color='#ff6b6b', width=3),
                marker=dict(size=8, symbol='circle')
            ))
            
            fig.update_layout(
                title="Monthly Spending Trends",
                xaxis_title="Month",
                yaxis_title="Amount (₹)",
                height=400,
                showlegend=True,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No spending trend data available")
    
    def _show_category_analysis_chart(self, insights: Dict):
        """Show category analysis chart."""
        category_spending = insights.get('category_spending_pattern', pd.Series())
        
        if not category_spending.empty:
            fig = px.pie(
                values=category_spending.values,
                names=category_spending.index,
                title="Spending by Category",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No category data available")
    
    def _show_time_patterns_chart(self, insights: Dict):
        """Show time patterns chart."""
        time_pattern = insights.get('time_pattern', pd.Series())
        
        if not time_pattern.empty:
            fig = px.bar(
                x=time_pattern.index,
                y=time_pattern.values,
                title="Spending by Time of Day",
                color_discrete_sequence=['#4ecdc4']
            )
            
            fig.update_layout(
                xaxis_title="Time of Day",
                yaxis_title="Amount (₹)",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No time pattern data available")
    
    def show_recommendations(self, insights: Dict, behavioral_insights: Dict):
        """Show personalized recommendations."""
        st.subheader("💡 Personalized Recommendations")
        
        recommendations = self._generate_recommendations(insights, behavioral_insights)
        
        for i, rec in enumerate(recommendations, 1):
            with st.expander(f"🎯 Recommendation {i}: {rec['title']}", expanded=True):
                st.write(rec['description'])
                if rec.get('action'):
                    st.info(f"**Action**: {rec['action']}")
    
    def _generate_recommendations(self, insights: Dict, behavioral_insights: Dict) -> List[Dict]:
        """Generate personalized recommendations."""
        recommendations = []
        
        # Savings rate recommendation
        savings_rate = insights.get('savings_rate', 0)
        if savings_rate < 20:
            recommendations.append({
                'title': 'Increase Your Savings Rate',
                'description': f'Your current savings rate is {savings_rate:.1f}%. Aim for at least 20% to build a strong financial foundation.',
                'action': 'Set up automatic transfers to a savings account on payday.'
            })
        
        # Stress spending recommendation
        stress_patterns = behavioral_insights.get('stress_patterns', {})
        stress_days = stress_patterns.get('stress_spending_days', {})
        high_freq_days = stress_days.get('high_frequency_days', 0)
        
        if high_freq_days > 10:
            recommendations.append({
                'title': 'Manage Stress Spending',
                'description': f'You had {high_freq_days} high-frequency spending days, which could indicate stress-related purchases.',
                'action': 'Try a 24-hour rule: wait 24 hours before making non-essential purchases.'
            })
        
        # Digital payment recommendation
        personality = behavioral_insights.get('personality_profile', {})
        digital_info = personality.get('digital_native_level', {})
        digital_ratio = digital_info.get('digital_ratio', 0)
        
        if digital_ratio < 0.5:
            recommendations.append({
                'title': 'Embrace Digital Payments',
                'description': f'Only {digital_ratio:.1%} of your transactions are digital. Digital payments offer better tracking and security.',
                'action': 'Start using UPI for small transactions and gradually increase digital payment usage.'
            })
        
        return recommendations 