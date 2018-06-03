from catalog.places import app as application

if __name__ == "__main__":
    application.secret_key = 'AKIAJ4UJCKHR4TOLPJRQ'
    application.debug = True
    application.run(host='18.220.11.125', port=80)
