from flask import Flask

from flask import render_template
from flask import request, redirect
from flask import session, flash
from flask import url_for
from flask import json 
from flask import make_response
from fpdf import FPDF

import mysql.connector

app = Flask(__name__)

app.secret_key = "YOUR_SECRET_KEY"

config = {
  'user': 'root',
  'password': 'root',
  'host': '127.0.0.1',

  'port': 8889,
  'database': 'mydb2',
  'raise_on_warnings': True
}

cnx = mysql.connector.connect(**config)

cursor = cnx.cursor(dictionary=True)
@app.route('/')
def homepage():
    return redirect(url_for('home'))

@app.route('/home', methods=['GET'])
def home():
    if session.get('admin'):
        return redirect(url_for('admin'))
    else:
        if session.get('logged_in'):        
            cursor.execute('SELECT u.Nom, u.Prenom, u.mail, u.tel FROM user u WHERE u.IdParent = %s', (session['user_id'],))
            results = cursor.fetchone()
            nom = results['Nom']
            prenom = results['Prenom']
            mail = results['mail']
            tel = results['tel']
            cursor.execute("SELECT e.IdEnfant, e.Nom, e.Prenom, e.classe, COUNT(r.enfant_IdEnfant) AS repas_count, r2.type AS regime_type, e.regime_idRegime FROM enfant e JOIN famille f ON e.IdEnfant = f.enfant_IdEnfant JOIN repas r ON e.IdEnfant = r.enfant_IdEnfant LEFT JOIN regime r2 ON e.regime_idRegime = r2.idRegime WHERE f.user_IdParent = %s AND r.jour_date BETWEEN DATE_FORMAT(CURRENT_DATE(), '%Y-%m-01') AND LAST_DAY(CURRENT_DATE()) GROUP BY e.IdEnfant", (session['user_id'],)) 
            enfants = cursor.fetchall()
            repas_total = 0
            for enfant in enfants:
                if enfant['regime_idRegime'] == 4:
                    repas_total += enfant['repas_count'] * 0.50
                else:
                    repas_total += enfant['repas_count'] * 3.50
            cursor.execute("SELECT COUNT(r.enfant_IdEnfant) AS repas_count FROM enfant e JOIN famille f ON e.IdEnfant = f.enfant_IdEnfant JOIN repas r ON e.IdEnfant = r.enfant_IdEnfant LEFT JOIN regime r2 ON e.regime_idRegime = r2.idRegime WHERE f.user_IdParent = %s AND r.jour_date BETWEEN DATE_FORMAT(CURRENT_DATE(), '%Y-%m-01') AND LAST_DAY(CURRENT_DATE())", (session['user_id'],))        
            enfants2 = cursor.fetchall()
            print(enfants)
            print(enfants2)
            cnx.commit();
            return render_template('hello.html', nom=nom, prenom=prenom, mail=mail, tel=tel, enfants=enfants, repas_total=repas_total)
        else:
            return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        nom = request.form['nom']
        prenom = request.form['prenom']
        mail = request.form['mail']
        tel = request.form['tel']
        identifiant = request.form['identifiant']
        mdp = request.form['mdp']
        cursor.execute('SELECT * FROM `user` WHERE IdParent=%s OR mail=%s OR tel=%s', (identifiant, mail, tel))
        user = cursor.fetchone()
        
        if user is not None:
            flash('Cet identifiant, mail ou numéro de téléphone existe déjà', 'error')
            return redirect(url_for('register'))
        cursor.execute('INSERT INTO `user` (`IdParent`,`mdp`,`Nom`,`prenom`,`mail`,`tel`) VALUES (%s,%s,%s,%s,%s,%s)',(identifiant, mdp, nom, prenom, mail, tel))
        cnx.commit()
        cursor.execute('SELECT * FROM `user` WHERE IdParent=%s AND mdp=%s', (identifiant, mdp))
        user = cursor.fetchone()
        if user is not None:
            session['logged_in'] = True
            session['user_id'] = user['IdParent']
            return redirect(url_for('home'))
        return redirect(url_for('home'))
    return render_template('inscription.html')

@app.route('/admin_page', methods=['GET', 'POST'])
def admin():

    if request.method == 'POST':
        classe = request.form['classe']
        cursor.execute('SELECT IdEnfant, Nom, Prenom, classe FROM enfant WHERE classe=%s',(classe,))
        enfants = cursor.fetchall()
        cursor.execute('SELECT DISTINCT jour_date FROM repas WHERE MONTH(jour_date) = MONTH(CURRENT_DATE()) AND enfant_IdEnfant IN (SELECT IdEnfant FROM enfant WHERE classe=%s)', (classe,))
        days = cursor.fetchall()
        return render_template('admin.html', enfants=enfants, days=days,classe=classe)
    else:
        return render_template('admin.html') 
    
@app.route('/delete_day', methods=['GET', 'POST'])
def delete_day():
    if request.method == 'POST':
        classe = request.form['classe']
        jour_date = request.form['jour_date']
        cursor.execute('DELETE FROM repas WHERE jour_date=%s AND enfant_IdEnfant IN (SELECT IdEnfant FROM enfant WHERE classe=%s)', (jour_date, classe))
        cnx.commit()
        return redirect(url_for('admin'))
    return redirect(url_for('admin'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        identifiant = request.form['identifiant']
        mdp = request.form['mdp']
        cursor.execute('SELECT * FROM `user` WHERE IdParent=%s AND mdp=%s', (identifiant, mdp))
        user = cursor.fetchone()
        if user is not None:
            session['logged_in'] = True
            session['user_id'] = user['IdParent']
            if user['admin'] == 1:
                session['admin'] = True
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('home'))
        else:
            flash('Identifiant ou mot de passe incorrect')
            return redirect(url_for('login'))
    if 'logged_in' in session:
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/inscription',methods=['GET','POST'])
def inscrire():
    existe_pas= True
    Present=False
    if 'logged_in' in session:
        if request.method == 'POST':
            if not request.form['prenom']:
                flash('Veuillez entrer un prénom')
            elif not request.form['nom']:
                flash('Veuillez entrer un nom')
            elif not request.form['classe']:
                flash('Veuillez entrer une classe')
            elif not request.form['regimeAlimentaire']:
                flash('Veuillez entrer un régime alimentaire')
            else:
                days = ['lundi', 'mardi', 'jeudi', 'vendredi']
                days_checked = []  
                days_ids = []     

                for day in days:
                    if request.form.get(day):
                        days_checked.append(day)
                        cursor.execute("SELECT `IdJour` FROM `formule` WHERE jour = %s", (day,))
                        jour = cursor.fetchone()['IdJour']
                        days_ids.append(jour)

                dates = []
                for day_idd in days_ids:
                    cursor.execute("SELECT date FROM jour WHERE formule_IdJour = %s", (day_idd,)) 
                    result = cursor.fetchall()
                    dates = dates + [row['date'] for row in result]
                    
                prenom = request.form['prenom']
                nom = request.form['nom']
                session["prenomE"] = prenom
                session["nomE"] = nom

                classe = request.form['classe']
                regimeAlimentaire = request.form['regimeAlimentaire']
                cursor.execute('SELECT idRegime FROM `regime` WHERE type = %s',(regimeAlimentaire,))
                idRegime = cursor.fetchone()['idRegime']

                cursor.execute('SELECT IdEnfant FROM `enfant` WHERE Nom = %s AND Prenom = %s', (nom, prenom))
                pareil = cursor.fetchone()

                if pareil is None:
                    existe_pas = True
                    Present = False
                    cursor.execute('INSERT INTO `enfant` (`Nom`, `Prenom`, `classe`,`regime_idRegime`) VALUES (%s,%s,%s,%s)',(nom, prenom, classe,idRegime))
                    idgosse = cursor.lastrowid

                    for day_id in days_ids:
                        cursor.execute('INSERT INTO `formenfant` (`Formule_IdJour`,`enfant_IdEnfant`) VALUES (%s,%s)',(day_id,idgosse))
                    
                    for date in dates:
                        cursor.execute('INSERT INTO repas (jour_date,enfant_IdEnfant) VALUES (%s,%s)',(date,idgosse))
                    cursor.execute('INSERT INTO `famille` (`enfant_IdEnfant`, `user_IdParent`) VALUES (%s,%s)',(idgosse,session['user_id']))
                    cnx.commit()
                    return redirect(url_for('home'))
                else:
                    cursor.execute('SELECT user_IdParent FROM `famille` WHERE enfant_IdEnfant = %s', (pareil["IdEnfant"],))
                    parent = cursor.fetchall()
                    parents = [row['user_IdParent'] for row in parent]
                    existe_pas = False
                    idgosse = cursor.lastrowid
                    print("1")
                    print(parents)
                    print(session['user_id'])
                    for parent in parents:
                        if parent == session['user_id'] and pareil is None:
                            existe_pas = False
                            print("2")
                        if parent == session['user_id'] and pareil is not None:
                            existe_pas = True
                            Present = True
                            print("3")
    else:
        existe_pas= True
        flash("Vous n'êtes pas connecté")
        return redirect(url_for('login'))
    return render_template('inscriptionCantine.html', existe_pas=existe_pas, Present=Present)

###
@app.route('/confirmer', methods=['GET','POST'])
def confirmer():
    if request.method == 'POST':
        box = request.form['box']
        if box is not None:
            prenom = session.get("prenomE")
            nom = session.get("nomE")
            print(nom, prenom)

            cursor.execute('SELECT IdEnfant FROM `enfant` WHERE Nom = %s AND Prenom = %s', (nom, prenom,))
            id = cursor.fetchone()["IdEnfant"]
            print (id)

            cursor.execute('INSERT INTO `famille` (`enfant_IdEnfant`, `user_IdParent`) VALUES (%s,%s)',(id,session['user_id']))
            cnx.commit()

    return redirect(url_for('home')) 

@app.route("/bondecommande")
def commande():
    cursor.execute("SELECT COUNT(r.jour_date) AS meals, DAYOFWEEK(r.jour_date) AS day_of_week, e.regime_idRegime AS diet_type FROM enfant e LEFT JOIN repas r ON e.IdEnfant = r.enfant_IdEnfant AND r.jour_date BETWEEN CURDATE() - INTERVAL DAYOFWEEK(CURDATE()) DAY AND CURDATE() + INTERVAL 6 - DAYOFWEEK(CURDATE()) DAY WHERE e.classe IN ('TPS', 'PS', 'MS', 'GS','CP', 'CE1', 'CE2', 'CM1', 'CM2') AND e.regime_idRegime = 0 GROUP BY DAYOFWEEK(r.jour_date), e.regime_idRegime ORDER BY DAYOFWEEK(r.jour_date)")
    type1_nursery_meals = cursor.fetchall()

    cursor.execute("SELECT COUNT(r.jour_date) AS meals, DAYOFWEEK(r.jour_date) AS day_of_week, e.regime_idRegime AS diet_type FROM enfant e LEFT JOIN repas r ON e.IdEnfant = r.enfant_IdEnfant AND r.jour_date BETWEEN CURDATE() - INTERVAL DAYOFWEEK(CURDATE()) DAY AND CURDATE() + INTERVAL 6 - DAYOFWEEK(CURDATE()) DAY WHERE e.classe IN ('TPS', 'PS', 'MS', 'GS','CP', 'CE1', 'CE2', 'CM1', 'CM2') AND e.regime_idRegime = 1 GROUP BY DAYOFWEEK(r.jour_date), e.regime_idRegime ORDER BY DAYOFWEEK(r.jour_date)")
    type2_nursery_meals = cursor.fetchall()

    cursor.execute("SELECT COUNT(r.jour_date) AS meals, DAYOFWEEK(r.jour_date) AS day_of_week, e.regime_idRegime AS diet_type FROM enfant e LEFT JOIN repas r ON e.IdEnfant = r.enfant_IdEnfant AND r.jour_date BETWEEN CURDATE() - INTERVAL DAYOFWEEK(CURDATE()) DAY AND CURDATE() + INTERVAL 6 - DAYOFWEEK(CURDATE()) DAY WHERE e.classe IN ('TPS', 'PS', 'MS', 'GS','CP', 'CE1', 'CE2', 'CM1', 'CM2') AND e.regime_idRegime = 2 GROUP BY DAYOFWEEK(r.jour_date), e.regime_idRegime ORDER BY DAYOFWEEK(r.jour_date)")
    type3_nursery_meals = cursor.fetchall()

    cursor.execute("SELECT COUNT(r.jour_date) AS meals, DAYOFWEEK(r.jour_date) AS day_of_week, e.regime_idRegime AS diet_type FROM enfant e LEFT JOIN repas r ON e.IdEnfant = r.enfant_IdEnfant AND r.jour_date BETWEEN CURDATE() - INTERVAL DAYOFWEEK(CURDATE()) DAY AND CURDATE() + INTERVAL 6 - DAYOFWEEK(CURDATE()) DAY WHERE e.classe IN ('TPS', 'PS', 'MS', 'GS','CP', 'CE1', 'CE2', 'CM1', 'CM2') AND e.regime_idRegime = 3 GROUP BY DAYOFWEEK(r.jour_date), e.regime_idRegime ORDER BY DAYOFWEEK(r.jour_date)")
    type4_nursery_meals = cursor.fetchall()

    cursor.execute("SELECT COUNT(r.jour_date) AS meals, DAYOFWEEK(r.jour_date) AS day_of_week, e.regime_idRegime AS diet_type FROM enfant e LEFT JOIN repas r ON e.IdEnfant = r.enfant_IdEnfant AND r.jour_date BETWEEN CURDATE() - INTERVAL DAYOFWEEK(CURDATE()) DAY AND CURDATE() + INTERVAL 6 - DAYOFWEEK(CURDATE()) DAY WHERE e.classe IN ('TPS', 'PS', 'MS', 'GS','CP', 'CE1', 'CE2', 'CM1', 'CM2') AND e.regime_idRegime = 4 GROUP BY DAYOFWEEK(r.jour_date), e.regime_idRegime ORDER BY DAYOFWEEK(r.jour_date)" )
    type5_nursery_meals = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(r.jour_date) AS meals, DAYOFWEEK(r.jour_date) AS day_of_week, e.regime_idRegime AS diet_type FROM enfant e LEFT JOIN repas r ON e.IdEnfant = r.enfant_IdEnfant AND r.jour_date BETWEEN CURDATE() - INTERVAL DAYOFWEEK(CURDATE()) DAY AND CURDATE() + INTERVAL 6 - DAYOFWEEK(CURDATE()) DAY WHERE e.regime_idRegime IN('0','1','2','3') GROUP BY DAYOFWEEK(r.jour_date) ORDER BY DAYOFWEEK(r.jour_date)")
    type6_nursery_meals = cursor.fetchall()

    return render_template('bondecommandeHebdo.html', type1_nursery_meals = type1_nursery_meals, type2_nursery_meals = type2_nursery_meals, type3_nursery_meals = type3_nursery_meals, type4_nursery_meals = type4_nursery_meals, type5_nursery_meals = type5_nursery_meals, type6_nursery_meals=type6_nursery_meals)


@app.route('/feuillePresence')
def presence():
    cursor.execute("SELECT IdEnfant, Nom, Prenom, classe, count(rl.jour_date) as lundi , count(rm.jour_date) as mardi , count(rj.jour_date) as jeudi  , count(rv.jour_date) as vendredi FROM enfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)) rl on IdEnfant = rl.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 1 DAY)) rm on IdEnfant = rm.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 3 DAY)) rj on IdEnfant = rj.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_ADD(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 1 DAY)) rv on IdEnfant = rv.enfant_IdEnfant WHERE classe ='TPS' group by IdEnfant;")
    tps = cursor.fetchall()
    cursor.execute("SELECT IdEnfant, Nom, Prenom, classe, count(rl.jour_date) as lundi , count(rm.jour_date) as mardi , count(rj.jour_date) as jeudi  , count(rv.jour_date) as vendredi FROM enfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)) rl on IdEnfant = rl.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 1 DAY)) rm on IdEnfant = rm.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 3 DAY)) rj on IdEnfant = rj.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_ADD(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 1 DAY)) rv on IdEnfant = rv.enfant_IdEnfant WHERE classe ='PS' group by IdEnfant;")
    ps = cursor.fetchall() 
    cursor.execute("SELECT IdEnfant, Nom, Prenom, classe, count(rl.jour_date) as lundi , count(rm.jour_date) as mardi , count(rj.jour_date) as jeudi  , count(rv.jour_date) as vendredi FROM enfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)) rl on IdEnfant = rl.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 1 DAY)) rm on IdEnfant = rm.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 3 DAY)) rj on IdEnfant = rj.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_ADD(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 1 DAY)) rv on IdEnfant = rv.enfant_IdEnfant WHERE classe ='MS' group by IdEnfant;")
    ms = cursor.fetchall() 
    cursor.execute("SELECT IdEnfant, Nom, Prenom, classe, count(rl.jour_date) as lundi , count(rm.jour_date) as mardi , count(rj.jour_date) as jeudi  , count(rv.jour_date) as vendredi FROM enfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)) rl on IdEnfant = rl.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 1 DAY)) rm on IdEnfant = rm.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 3 DAY)) rj on IdEnfant = rj.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_ADD(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 1 DAY)) rv on IdEnfant = rv.enfant_IdEnfant WHERE classe ='GS' group by IdEnfant;")
    gs = cursor.fetchall() 
    cursor.execute("SELECT IdEnfant, Nom, Prenom, classe, count(rl.jour_date) as lundi , count(rm.jour_date) as mardi , count(rj.jour_date) as jeudi  , count(rv.jour_date) as vendredi FROM enfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)) rl on IdEnfant = rl.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 1 DAY)) rm on IdEnfant = rm.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 3 DAY)) rj on IdEnfant = rj.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_ADD(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 1 DAY)) rv on IdEnfant = rv.enfant_IdEnfant WHERE classe ='CP' group by IdEnfant;")
    cp = cursor.fetchall() 
    cursor.execute("SELECT IdEnfant, Nom, Prenom, classe, count(rl.jour_date) as lundi , count(rm.jour_date) as mardi , count(rj.jour_date) as jeudi  , count(rv.jour_date) as vendredi FROM enfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)) rl on IdEnfant = rl.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 1 DAY)) rm on IdEnfant = rm.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 3 DAY)) rj on IdEnfant = rj.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_ADD(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 1 DAY)) rv on IdEnfant = rv.enfant_IdEnfant WHERE classe ='CE1' group by IdEnfant;")
    ce1 = cursor.fetchall() 
    cursor.execute("SELECT IdEnfant, Nom, Prenom, classe, count(rl.jour_date) as lundi , count(rm.jour_date) as mardi , count(rj.jour_date) as jeudi  , count(rv.jour_date) as vendredi FROM enfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)) rl on IdEnfant = rl.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 1 DAY)) rm on IdEnfant = rm.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 3 DAY)) rj on IdEnfant = rj.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_ADD(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 1 DAY)) rv on IdEnfant = rv.enfant_IdEnfant WHERE classe ='CE2' group by IdEnfant;")
    ce2 = cursor.fetchall() 
    cursor.execute("SELECT IdEnfant, Nom, Prenom, classe, count(rl.jour_date) as lundi , count(rm.jour_date) as mardi , count(rj.jour_date) as jeudi  , count(rv.jour_date) as vendredi FROM enfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)) rl on IdEnfant = rl.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 1 DAY)) rm on IdEnfant = rm.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 3 DAY)) rj on IdEnfant = rj.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_ADD(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 1 DAY)) rv on IdEnfant = rv.enfant_IdEnfant WHERE classe ='CM1' group by IdEnfant;")
    cm1 = cursor.fetchall() 
    cursor.execute("SELECT IdEnfant, Nom, Prenom, classe, count(rl.jour_date) as lundi , count(rm.jour_date) as mardi , count(rj.jour_date) as jeudi  , count(rv.jour_date) as vendredi FROM enfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)) rl on IdEnfant = rl.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 1 DAY)) rm on IdEnfant = rm.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) - 3 DAY)) rj on IdEnfant = rj.enfant_IdEnfant LEFT JOIN (select * from repas where jour_date = DATE_ADD(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 1 DAY)) rv on IdEnfant = rv.enfant_IdEnfant WHERE classe ='CM2' group by IdEnfant;")
    cm2 = cursor.fetchall()    
    return render_template('feuillepresence.html',tps=tps,ps=ps,ms=ms,gs=gs,cp=cp,ce1=ce1,ce2=ce2,cm1=cm1,cm2=cm2)


@app.route('/calendrier',methods=['GET','POST'])
def calendrier(resultat=None, gosse=None):
    dates = []
    if 'logged_in' in session:
        if request.method == 'POST':

            enfant = request.form['enfant']

            cursor.execute("SELECT IdEnfant FROM enfant WHERE Prenom = %s", (enfant,))
            id = cursor.fetchone()
            session["id"] = id['IdEnfant']

            cursor.execute('SELECT jour_date FROM repas WHERE enfant_IdEnfant = %s',(id['IdEnfant'],))
            resultats = cursor.fetchall()
            dates = [row['jour_date'].strftime("%Y-%m-%d") for row in resultats]
        cursor.execute('SELECT e.IdEnfant, e.Nom, e.Prenom, e.classe FROM enfant e JOIN famille f ON e.IdEnfant = f.enfant_IdEnfant WHERE f.user_IdParent = %s', (session['user_id'],))
        enfants = cursor.fetchall()
        cnx.commit()
        return render_template('calendrier.html', resultat=dates, enfants=enfants)
    else:
        flash("Vous n'êtes pas connecté")
        return redirect(url_for('login'))
        

@app.route('/ajouter',methods=['GET','POST'])
def ajouter():

    if request.method == 'POST':
        date = request.form.get('box1')
        date2 = request.form.get('box2')

        id = session.get("id")
        print(id)
        print(date)
        print(date2)

        if date:
            cursor.execute("INSERT INTO repas (jour_date,enfant_IdEnfant) VALUES (%s,%s)",(date, id))
            cnx.commit()
        if date2:
            cursor.execute('DELETE FROM repas WHERE jour_date=%s AND enfant_IdEnfant=%s', (date2, id))
            cnx.commit()

    return redirect(url_for('calendrier'))

@app.route('/modif', methods=['GET'])
def modif():
    if session.get('logged_in'):
        cursor.execute('SELECT u.Nom, u.Prenom, u.mail, u.tel, u.IdParent, u.mdp FROM user u WHERE u.IdParent = %s', (session['user_id'],))
        results = cursor.fetchone()

        nom = results['Nom']
        prenom = results['Prenom']
        mail = results['mail']
        tel = results['tel']
        id = results['IdParent']
        mdp = results['mdp']

        cnx.commit()

        return render_template('modif.html', nom=nom, prenom=prenom, mail=mail, tel=tel, mdp=mdp, id=id)
    else:
        return render_template('hello.html')

@app.route('/modification', methods=['GET','POST'])
def modification():
    if session.get('logged_in'):
        if request.method == 'POST':

            nom2 = request.form['nom']
            prenom2 = request.form['prenom']
            mail2 = request.form['mail']
            tel2 = request.form['tel']
            id2 = request.form['identifiant']
            mdp2 = request.form['mdp']

            cursor.execute('SELECT enfant_IdEnfant FROM `famille` WHERE user_IdParent=%s',(session['user_id'],))
            enfants = cursor.fetchall()

            sql = "DELETE FROM famille WHERE user_IdParent=%s"
            value = (session['user_id'],)
            cursor.execute(sql, value)

            sql = "DELETE FROM user WHERE IdParent=%s"
            value = (session['user_id'],)
            cursor.execute(sql, value)

            cursor.execute('INSERT INTO `user` (`IdParent`,`mdp`,`Nom`,`prenom`,`mail`,`tel`) VALUES (%s,%s,%s,%s,%s,%s)',(id2, mdp2, nom2, prenom2, mail2, tel2))
            session['user_id'] = id2
            for enfant in enfants:
                    cursor.execute('INSERT INTO `famille` (`enfant_IdEnfant`, `user_IdParent`) VALUES (%s,%s)',(enfant['enfant_IdEnfant'], session['user_id']))

            cnx.commit()

            return redirect(url_for('home'))
        else:
            return redirect(url_for('home'))
    else:
        return redirect(url_for('home'))