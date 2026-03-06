import logging
import time
from shared.database.structural_db import StructuralDatabaseManager
from shared.data.structural_parsers import StructParsers
from shared.data.parsers import FireCurveParser

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    # Define input paths
    xml_path = input("Enter SAFIR XML file path: ").strip()
    db_path = input("Enter SQLite database path: ").strip()
    fct_path = input("Enter FCT file path: ").strip()

    start_time = time.perf_counter()

    # Initialize the ThermalDatabaseManager
    db = StructuralDatabaseManager(db_path)

    # Clear the database (optional, based on user confirmation)
    db.clear_database()

    # Create tables in the database
    db.create_tables()
    logging.info("Database setup completed.")

    # Initialize the parser and postprocessor
    XML_parser = StructParsers(xml_path, db)
    XML_parser.parse_and_store_tables()
    logging.info("Xml data parsing and storing completed.")

    # FCT parser
    FCT_parser = FireCurveParser(fct_path, db)
    FCT_parser.parse_and_store_tables()

    # Postprocessing Additional Tables for views
        # postprocessor = PostProcessor(db)
        # postprocessor.calc_maxtemp_bymaterial()
    db.create_views()

    end_time = time.perf_counter()  # End the timer
    elapsed_time = end_time - start_time
    logging.info(f"Time taken for compiling: {elapsed_time:.2f} seconds")
