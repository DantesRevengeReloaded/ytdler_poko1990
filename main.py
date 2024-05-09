# Import the modules
import pokodler_ui_config


# Define the main function
def main():
    # Load the configuration
    #pokodler_config.load_config()

    # Create the UI
    #ui = pokodler_ui

    # Create the downloader manager
    #dl_manager = pokodler_dl_manager.PokodlerDLManager()

    # Create the database manager
    #db_manager = pokodler_db_manager.PokodlerDBManager()

    # Set the UI callbacks
    #ui.set_download_callback(dl_manager.download_video)
    #ui.set_database_callback(db_manager.get_videos)

    # Start the UI
    pokodler_ui_config

# Call the main function
if __name__ == '__main__':
    main()