import os

# Define the necessary directories
directories = {
    'playlists': './data/playlists',
    'trivia': './data/trivia',
    'minigames': './data/minigames'
}

def check_dependencies():
    """
    Check if required directories exist, and if not, create them.
    """
    for key, directory in directories.items():
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Directory '{directory}' created.")
        else:
            print(f"Directory '{directory}' already exists.")

