
import os
import streamlit.components.v1 as components

# Declare the component
_component_func = components.declare_component(
    "news_tracker",
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
)

def news_tracker(articles, action_label="Action", show_score=True, show_remove=True, key=None):
    """
    Render a list of articles with tracking enabled.
    
    Args:
        articles (list): List of dicts with {id, title, media, summary, url, score, is_action_done}.
        action_label (str): Label for the action button (e.g. "Rate", "Save").
        show_score (bool): Whether to show the score.
        show_remove (bool): Whether to show the remove (X) button.
        key (str): Streamlit unique key.
        
    Returns:
        dict: Event data {event: 'hover'|'click'|'action_request'|'remove_request', target_id: ..., ...}
    """
    return _component_func(articles=articles, action_label=action_label, 
                           show_score=show_score, show_remove=show_remove, 
                           key=key, default=None)
