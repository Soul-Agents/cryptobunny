from app import create_app
import os
app = create_app()

if __name__ == '__main__':  
        is_dev = os.getenv('DEV_MODE')
        app.run(host='0.0.0.0', port=8000, debug=is_dev)