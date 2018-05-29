from places import app as application

if __name__ == "__main__":
    application.secret_key = 'AKIAJ4UJCKHR4TOLPJRQ'
    application.debug = True
    application.run(host='13.58.191.212', port=80)