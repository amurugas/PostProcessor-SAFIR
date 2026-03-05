import logging
import shared.data.parsers as parsers
from shared.database.thermal_db import ThermalDatabaseManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    # Define the database path
    xml_path = input("Enter SAFIR XML file path: ").strip()
    db_path = input("Enter SQLite database path: ").strip()
    fct_path = 'data/S1C.fct'

    # Initialize the ThermalDatabaseManager
    db_manager = ThermalDatabaseManager(db_path)


    # Clear the database (optional, based on user confirmation)
    db_manager.clear_database()

    # Log the completion of the database setup
    logging.info("2D Thermal database setup completed.")

    root = parsers.XmlParser(xml_path).parse()


    # db_path = 'W24.db'
    # xml_path = 'w24x55_ins.XML'


    parser = FileParser(db)
    postprocessor = PostProcessor(db)

    db.clear_database()
    parser.parse_xml_data(xml_path)
    parser.store_fire_curve(fct_path)
    postprocessor.calc_maxtemp_bymaterial()
    db.create_views()