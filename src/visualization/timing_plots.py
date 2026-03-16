import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional

def plot_feature_distribution(
    df: pd.DataFrame, 
    feature_col: str, 
    label_col: Optional[str] = None,
    title: Optional[str] = None,
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot the distribution of a single timing feature, optionally split by a binary label.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame of features and labels.
    feature_col : str
        Name of the continuous feature column to plot.
    label_col : str, optional
        Binary qualitative label to group by (e.g., high/low quality).
    title : str, optional
        Custom title for the plot.
    save_path : str, optional
        If provided, saves the figure to this path.
        
    Returns
    -------
    plt.Figure
        The resulting matplotlib figure.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    if label_col is not None and label_col in df.columns:
        sns.kdeplot(
            data=df, 
            x=feature_col, 
            hue=label_col, 
            fill=True, 
            common_norm=False,
            alpha=0.5,
            ax=ax
        )
    else:
        sns.kdeplot(
            data=df, 
            x=feature_col, 
            fill=True, 
            ax=ax
        )
        
    if title:
        ax.set_title(title)
    else:
        ax.set_title(f'Distribution of {feature_col}')
        
    ax.set_xlabel(feature_col)
    ax.set_ylabel('Density')
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
    return fig

def plot_correlation_matrix(
    df: pd.DataFrame,
    feature_cols: list,
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot a heatmap of Pearson correlations between timing features.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame of features.
    feature_cols : list
        List of continuous feature columns to include in the matrix.
    save_path : str, optional
        If provided, saves the figure to this path.
        
    Returns
    -------
    plt.Figure
        The resulting seaborn map as a matplotlib figure.
    """
    # Select available columns
    cols_to_use = [col for col in feature_cols if col in df.columns]
    
    corr = df[cols_to_use].corr()
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    sns.heatmap(
        corr, 
        annot=True, 
        cmap='coolwarm', 
        vmin=-1, 
        vmax=1, 
        center=0,
        fmt='.2f',
        square=True,
        linewidths=.5,
        ax=ax
    )
    
    ax.set_title('Feature Correlation Matrix')
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
    return fig
