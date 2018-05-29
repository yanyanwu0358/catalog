from places import app as application

if __name__ == "__main__":
    application.secret_key = 'AKIAJ4UJCKHR4TOLPJRQ'
    application.debug = True
    application.run(host='0.0.0.0', port=5000)