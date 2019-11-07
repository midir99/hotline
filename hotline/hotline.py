import dbfunctions
import configuration
import logging
import sys
import PyQt5
import ui

if __name__ == '__main__':
    configuration.configure_logging('DEBUG')
    dbfunctions.set_dbpath("C:/Users/jorge/tangerine/estancia/hotline/resources/hotline.db")
    logging.info('Logging has been configured!')
    try:
        if configuration.running_as_a_python_process():
            logging.info('Running as a Python process')
            dbfunctions.set_dbpath(configuration.debug_database_path())
        else:
            logging.info('Not running as a Python process')
            dbfunctions.set_dbpath(configuration.debug_database_path())
    except FileNotFoundError as f:
        logging.critical(f)
        logging.info('Closing application...')
        sys.exit(1)
    except Exception as e:
        logging.error(e)

    configuration.setup_network_information()

    app = PyQt5.QtWidgets.QApplication(sys.argv)
    window = ui.HotlineMainWindow()
    window.show()
    exit_code = app.exec_()
    logging.info('Closing app, setting some values in the DB')
    sys.exit(exit_code)