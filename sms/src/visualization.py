"""
Visualization module for SMS transaction analysis.
Provides consistent chart creation with error handling and styling.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Optional, Any
import logging
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)


class VisualizationEngine:
    """Centralized visualization engine with consistent styling and error handling."""
    
    def __init__(self):
        """Initialize visualization engine."""
        # Define consistent color schemes
        self.colors = {
            'primary': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
            'category': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f'],
            'financial': {'income': '#2ca02c', 'expense': '#d62728', 'savings': '#1f77b4'},
            'anomaly': {'normal': '#1f77b4', 'anomaly': '#d62728', 'threshold': '#ff7f0e'}
        }
    
    def create_bar_chart(self, data: pd.Series, title: str = "", max_items: int = 10) -> go.Figure:
        """
        Create a bar chart from pandas Series.
        
        Args:
            data: Pandas Series with data
            title: Chart title
            max_items: Maximum number of items to display
            
        Returns:
            Plotly figure object
        """
        try:
            if data.empty:
                return self._create_empty_chart(title)
            
            # Limit items if needed
            if len(data) > max_items:
                data = data.head(max_items)
            
            fig = px.bar(
                x=data.index,
                y=data.values,
                title=title,
                color_discrete_sequence=self.colors['primary']
            )
            
            fig.update_layout(
                xaxis_title="",
                yaxis_title="Amount (₹)",
                showlegend=False,
                height=400
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating bar chart: {e}")
            return self._create_error_chart(title)
    
    def create_line_chart(self, data: pd.Series, title: str = "") -> go.Figure:
        """
        Create a line chart from pandas Series.
        
        Args:
            data: Pandas Series with data
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        try:
            if data.empty:
                return self._create_empty_chart(title)
            
            fig = px.line(
                x=data.index,
                y=data.values,
                title=title,
                color_discrete_sequence=self.colors['primary']
            )
            
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Amount (₹)",
                showlegend=False,
                height=400
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating line chart: {e}")
            return self._create_error_chart(title)
    
    def create_pie_chart(self, data: pd.Series, title: str = "", max_items: int = 8) -> go.Figure:
        """
        Create a pie chart from pandas Series.
        
        Args:
            data: Pandas Series with data
            title: Chart title
            max_items: Maximum number of items to display
            
        Returns:
            Plotly figure object
        """
        try:
            if data.empty:
                return self._create_empty_chart(title)
            
            # Limit items if needed
            if len(data) > max_items:
                # Keep top items and group others
                top_data = data.head(max_items - 1)
                others_sum = data.iloc[max_items - 1:].sum()
                data = pd.concat([top_data, pd.Series({'Others': others_sum})])
            
            fig = px.pie(
                values=data.values,
                names=data.index,
                title=title,
                color_discrete_sequence=self.colors['category']
            )
            
            fig.update_layout(height=400)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating pie chart: {e}")
            return self._create_error_chart(title)
    
    def create_pattern_break_chart(self, chart_data: Dict) -> go.Figure:
        """
        Create pattern break chart with anomalies highlighted.
        
        Args:
            chart_data: Dictionary with chart data
            
        Returns:
            Plotly figure object
        """
        try:
            data = chart_data.get('data', pd.DataFrame())
            mean = chart_data.get('mean', 0)
            threshold = chart_data.get('threshold', 0)
            
            if data.empty:
                return self._create_empty_chart("Monthly Spending with Anomalies")
            
            fig = px.bar(
                data,
                x='transaction_date',
                y='amount',
                color='is_anomaly',
                color_discrete_map={True: self.colors['anomaly']['anomaly'], False: self.colors['anomaly']['normal']},
                title="Monthly Spending with Anomalies Highlighted"
            )
            
            # Add mean line
            fig.add_hline(
                y=mean,
                line_dash="dot",
                line_color=self.colors['anomaly']['threshold'],
                annotation_text=f"Average: ₹{mean:,.0f}"
            )
            
            # Add threshold lines
            fig.add_hline(
                y=mean + threshold,
                line_dash="dash",
                line_color=self.colors['anomaly']['threshold'],
                annotation_text="Upper Threshold"
            )
            
            fig.add_hline(
                y=mean - threshold,
                line_dash="dash",
                line_color=self.colors['anomaly']['threshold'],
                annotation_text="Lower Threshold"
            )
            
            fig.update_layout(
                xaxis_title="Month",
                yaxis_title="Amount (₹)",
                height=400
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating pattern break chart: {e}")
            return self._create_error_chart("Monthly Spending with Anomalies")
    
    def create_spike_chart(self, spike_data: pd.DataFrame) -> go.Figure:
        """
        Create enhanced spending spike chart with multiple levels and insights.
        
        Args:
            spike_data: DataFrame with enhanced spike data including spike_level
            
        Returns:
            Plotly figure object
        """
        try:
            if spike_data.empty:
                return self._create_empty_chart("Spending Spikes")
            
            # Create color mapping for spike levels
            spike_colors = {
                'Extreme': '#d62728',  # Red for extreme spikes
                'High': '#ff7f0e',     # Orange for high spikes
                'Moderate': '#1f77b4', # Blue for moderate spikes
                'Normal': '#2ca02c'    # Green for normal
            }
            
            # Create the chart
            fig = px.bar(
                spike_data,
                x='transaction_date',
                y='amount',
                color='spike_level' if 'spike_level' in spike_data.columns else 'merchant_canonical',
                title="Spending Breakdown on Spike Days",
                color_discrete_map=spike_colors if 'spike_level' in spike_data.columns else None,
                color_discrete_sequence=self.colors['category'] if 'spike_level' not in spike_data.columns else None
            )
            
            # Add hover information
            if 'spike_level' in spike_data.columns:
                fig.update_traces(
                    hovertemplate="<b>Date:</b> %{x}<br>" +
                                "<b>Amount:</b> ₹%{y:,.2f}<br>" +
                                "<b>Spike Level:</b> %{marker.color}<br>" +
                                "<b>Merchant:</b> %{customdata}<br>" +
                                "<extra></extra>",
                    customdata=spike_data['merchant_canonical']
                )
            else:
                fig.update_traces(
                    hovertemplate="<b>Date:</b> %{x}<br>" +
                                "<b>Amount:</b> ₹%{y:,.2f}<br>" +
                                "<b>Merchant:</b> %{marker.color}<br>" +
                                "<extra></extra>"
                )
            
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Amount (₹)",
                height=500,
                showlegend=True,
                legend_title="Spike Level" if 'spike_level' in spike_data.columns else "Merchant"
            )
            
            # Add threshold lines if available
            if 'spike_level' in spike_data.columns:
                # Add reference line for average spending
                avg_amount = spike_data['amount'].mean()
                fig.add_hline(
                    y=avg_amount,
                    line_dash="dash",
                    line_color="gray",
                    annotation_text=f"Average: ₹{avg_amount:,.0f}",
                    annotation_position="top right"
                )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating spike chart: {e}")
            return self._create_error_chart("Spending Spikes")
    
    def create_income_expense_chart(self, monthly_income: pd.Series, monthly_expense: pd.Series) -> go.Figure:
        """
        Create income vs expense comparison chart.
        
        Args:
            monthly_income: Series with monthly income data
            monthly_expense: Series with monthly expense data
            
        Returns:
            Plotly figure object
        """
        try:
            if monthly_income.empty and monthly_expense.empty:
                return self._create_empty_chart("Monthly Income vs Expenses")
            
            # Create combined dataframe
            chart_data = []
            
            for month in monthly_income.index:
                chart_data.append({
                    'Month': str(month),
                    'Amount': monthly_income[month],
                    'Type': 'Income'
                })
            
            for month in monthly_expense.index:
                chart_data.append({
                    'Month': str(month),
                    'Amount': monthly_expense[month],
                    'Type': 'Expense'
                })
            
            df = pd.DataFrame(chart_data)
            
            fig = px.bar(
                df,
                x='Month',
                y='Amount',
                color='Type',
                barmode='group',
                title="Monthly Income vs Expenses",
                color_discrete_map=self.colors['financial']
            )
            
            fig.update_layout(
                xaxis_title="Month",
                yaxis_title="Amount (₹)",
                height=400
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating income expense chart: {e}")
            return self._create_error_chart("Monthly Income vs Expenses")
    
    def create_time_series_chart(self, data: pd.Series, title: str = "") -> go.Figure:
        """
        Create time series chart with trend analysis.
        
        Args:
            data: Pandas Series with time series data
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        try:
            if data.empty:
                return self._create_empty_chart(title)
            
            fig = go.Figure()
            
            # Add main line
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data.values,
                mode='lines+markers',
                name='Actual',
                line=dict(color=self.colors['primary'][0])
            ))
            
            # Add trend line
            if len(data) > 1:
                x_numeric = range(len(data))
                z = np.polyfit(x_numeric, data.values, 1)
                p = np.poly1d(z)
                trend_line = p(x_numeric)
                
                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=trend_line,
                    mode='lines',
                    name='Trend',
                    line=dict(color=self.colors['primary'][1], dash='dash')
                ))
            
            fig.update_layout(
                title=title,
                xaxis_title="Time",
                yaxis_title="Amount (₹)",
                height=400,
                showlegend=True
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating time series chart: {e}")
            return self._create_error_chart(title)
    
    def create_heatmap(self, data: pd.DataFrame, title: str = "") -> go.Figure:
        """
        Create heatmap for correlation or frequency analysis.
        
        Args:
            data: DataFrame with data for heatmap
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        try:
            if data.empty:
                return self._create_empty_chart(title)
            
            fig = px.imshow(
                data,
                title=title,
                color_continuous_scale='Blues'
            )
            
            fig.update_layout(height=400)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating heatmap: {e}")
            return self._create_error_chart(title)
    
    def _create_empty_chart(self, title: str) -> go.Figure:
        """Create empty chart with message."""
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            title=title,
            height=400,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        return fig
    
    def _create_error_chart(self, title: str) -> go.Figure:
        """Create error chart with message."""
        fig = go.Figure()
        fig.add_annotation(
            text="Error loading chart",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="red")
        )
        fig.update_layout(
            title=title,
            height=400,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        return fig 