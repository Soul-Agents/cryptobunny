from app import create_app

app = create_app()

if __name__ == '__main__':
    # This will only run in development
    app.run(debug=True, host='0.0.0.0', port=8000)