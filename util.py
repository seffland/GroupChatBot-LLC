# Utility functions for the bot

def fix_mojibake(text):
    from ftfy import fix_text
    return fix_text(text)
