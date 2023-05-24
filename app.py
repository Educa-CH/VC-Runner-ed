from flask import Flask, render_template, jsonify, session, request, redirect, url_for
from configparser import ConfigParser
from flask_talisman import Talisman
from flask_session import Session
from flask_cors import CORS
import qrcode
import requests
import json

app = Flask(__name__)

CORS(app)

talisman = Talisman(app, content_security_policy={
    'default-src': ["'self'", "*", "'unsafe-inline'"],
    'frame-ancestors': ["'self'", '*'],
    'style-src-elem': ["'self'", 'data:']
})


app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_THRESHOLD'] = 500  # Set a threshold for the number of files before cleanup
Session(app)

config = ConfigParser()
config.read('config.ini')
app.secret_key = config.get('DEFAULT', 'SECRET_KEY', )
connection_url = config.get('ENDPOINTS', 'CONNECTION_URL').strip("'")
issuer_url = config.get('ENDPOINTS', 'ISSUER_URL').strip("'")
cred_def = config.get('CREDENTIAL_DEFINITION', 'CREDENTIAL_DEFINITION').strip("'")
attr1 = config.get('ATTRIBUTES', 'ATTR1').strip("'")
attr2 = config.get('ATTRIBUTES', 'ATTR2').strip("'")
attr3 = config.get('ATTRIBUTES', 'ATTR3').strip("'")


# allow site to be embedded in educa.ch 
# potentially used to emebed as iFrame
 
#@app.after_request
#def add_header(response):
#    response.headers['X-Frame-Options'] = 'ALLOW-FROM https://educa.ch'
#    return response

@app.route('/de')
def set_language_de():
    session['lang'] = 'de'
    return redirect(url_for('index'))

@app.route('/fr')
def set_language_fr():
    session['lang'] = 'fr'
    return redirect(url_for('index'))


@app.route('/')
def index():
    # set default language to german if not set
    if 'lang' not in session:
        session['lang'] = 'de'

    url = connection_url+ '/connection/invitation'
    response = requests.post(url)
    data = json.loads(response.text)
    dynamic_url = data['invitationUrl']
    session['connection'] = data['connectionId']
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=6, border=4)
    qr.add_data(dynamic_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save("static/images/dynamic_url_qr.png")  # Save the QR code image to a file

    # Set the prompt based on the language
    if session['lang'] == 'de':
        prompt = 'Scannen Sie den QR-Code mit Ihrer elektronischen Brieftasche (Lissi Wallet) und folgen Sie den weiteren Schritten in der App.'
        notice = 'Hinweis: Der Educa Agent dient nur zu Demonstrationszwecken und ist daher nicht verifiziert. Bitte nehmen Sie die Verbindungseinladung trotzdem an.'
    elif session['lang'] == 'fr':
        prompt = 'Scannez le code QR avec votre portefeuille électronique (Lissi wallet) et suivez les étapes suivantes dans l\'application.'
        notice = 'Remarque: l\'Educa Agent ne sert qu\'à des fins de démonstration et n\'est donc pas vérifié. Veuillez tout de même accepter l\'invitation pour vous connecter.'

    return render_template('index.html', qr_image='static/images/dynamic_url_qr.png', prompt=prompt, notice=notice)

@app.route('/check-connection/')
def check_connection():
    # Check the connection status by making a GET request to the API endpoint
    url = connection_url+  '/connection/' + session['connection'] 
    response = requests.get(url)
    if response.text == '"established"':
        # Connection has been established
        return jsonify({'status': 'connected'})
    else:
        # Connection has not been established
        return jsonify({'status': 'not connected'})

@app.route('/name', methods=['POST', 'GET'])      
def name():
    if request.method == 'POST':
        prename = request.form['prename']
        surname = request.form['surname']
        institution = request.form['institution']
        # Make a POST request to the API endpoint
        url = issuer_url + '/issue/process'
        data = {
            "connectionId": session['connection'],
            "credentialDefinitionId": cred_def,
            "attributes": {
                attr1: prename,
                attr2: surname,
                attr3: institution
            },
            "userId": "Anonymous"
        }        

        headers = {"Content-Type": "application/json"}

        response = requests.post(
            url,
            json=data,
            headers=headers)
        
        if response.status_code == 200:
            data = json.loads(response.text)
            session['processId'] = data['processId']

            if session['lang'] == 'de':
                prompt = 'Bitte akzeptieren Sie den gesendeten digitalen Nachweis in Ihrer elektronischen Brieftasche (Lissi Wallet).'
                notice = 'Hinweis: Der Educa Agent dient nur zu Demonstrationszwecken und ist daher nicht verifiziert. Bitte nehmen Sie den digitalen Nachweis trotzdem an.'
            elif session['lang'] == 'fr':
                prompt = 'Veuillez accepter le justificatif numérique envoyé dans votre portefeuille électronique (Lissi wallet).'   
                notice = 'Remarque: l\'Educa Agent ne sert qu\'à des fins de démonstration et n\'est donc pas vérifié. Veuillez tout de même accepter le justificatif numérique.' 

            return render_template('loading.html', prompt=prompt, notice=notice)

        else:
            return render_template('failure.html')    
    else:
        # Set the prompt based on the language
        if session['lang'] == 'de':
            prompt = 'Bitte füllen Sie das Formular aus und klicken Sie auf «absenden».'
            prename = 'Vorname:'
            surname = 'Name:'
            button = 'absenden'
        elif session['lang'] == 'fr':
            prompt = 'Veuillez remplir le formulaire et cliquer sur «envoyer».'
            prename = 'Prénom:'
            surname = 'Nom:'
            button = 'envoyer'

        #just show the page
        return render_template('name.html', prompt=prompt, button=button, prename=prename, surname=surname)


@app.route('/loading/')
def loading():
    # Check the Acception status by making a GET request to the API endpoint
    url = issuer_url+ '/issue/process/' + session['processId'] + '/state'
    response = requests.get(url)
    if response.text != '"IN_PROGRESS"':
        # Credential has been accepted
        return jsonify({'status': 'accepted'})
    else:
        # Credential has not been accepted
        return jsonify({'status': 'not accepted'})

@app.route('/success')
def success():
    if session['lang'] == 'de':
        prompt = 'Herzliche Gratulation, Sie haben soeben den digitalen Nachweis als agent novateur erhalten.'
    elif session['lang'] == 'fr':
        prompt = 'Félicitations, vous venez de recevoir votre justificatif numérique d\'agent novateur.'
    return render_template('success.html', prompt=prompt)        
  

if __name__ == "__main__":
    app.run(debug=False)    