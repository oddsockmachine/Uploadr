from datetime import datetime
from flask import Flask,session, request, flash, url_for, redirect, render_template, abort ,g, send_from_directory
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.login import login_user , logout_user , current_user , login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from os.path import isfile
from os.path import join as pjoin


app = Flask(__name__)
app.config.from_pyfile('uploadr.cfg')
db = SQLAlchemy(app)


login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = 'login'

class User(db.Model):
    __tablename__ = "users"
    id = db.Column('user_id',db.Integer , primary_key=True)
    username = db.Column('username', db.String(20), unique=True , index=True)
    password = db.Column('password' , db.String(250))
    email = db.Column('email',db.String(50),unique=True , index=True)
    registered_on = db.Column('registered_on' , db.DateTime)
    uploads = db.relationship('Upload' , backref='user',lazy='dynamic')

    def __init__(self , username ,password , email):
        self.username = username
        self.set_password(password)
        self.email = email
        self.registered_on = datetime.utcnow()


    def set_password(self , password):
        self.password = generate_password_hash(password)

    def check_password(self , password):
        return check_password_hash(self.password , password)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return '<User %r>' % (self.username)

class Upload(db.Model):
    __tablename__ = 'uploads'
    id = db.Column('upload_id', db.Integer, primary_key=True)
    title = db.Column(db.String(60))
    text = db.Column(db.String)
    done = db.Column(db.Boolean)
    pub_date = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))

    def __init__(self, title, text):
        self.title = title
        self.text = text
        self.done = False
        self.pub_date = datetime.utcnow()


if not isfile('app.db'):
    db.create_all()


@app.route('/')
@login_required
def index():
    return render_template('index.html',
        uploads=Upload.query.filter_by(user_id = g.user.id).order_by(Upload.pub_date.desc()).all()
    )

  
  
@app.route('/drop')
@login_required
def drop():
    return render_template('drop.html')



@app.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        if not request.form['title']:
            flash('Title is required', 'error')
        elif not request.form['text']:
            flash('Text is required', 'error')
        else:
            upload = Upload(request.form['title'], request.form['text'])
            upload.user = g.user
            db.session.add(upload)
            db.session.commit()
            flash('Upload item was successfully created')
            return redirect(url_for('index'))
    return render_template('new.html')

@app.route('/uploads/<int:upload_id>', methods = ['GET' , 'POST'])
@login_required
def show_or_update(upload_id):
    upload_item = Upload.query.get(upload_id)
    if request.method == 'GET':
        return render_template('view.html',upload=upload_item)
    if upload_item.user.id == g.user.id:
        upload_item.title = request.form['title']
        upload_item.text  = request.form['text']
        upload_item.done  = ('done.%d' % upload_id) in request.form
        db.session.commit()
        return redirect(url_for('index'))
    flash('You are not authorized to edit this upload item','error')
    return redirect(url_for('show_or_update',upload_id=upload_id))


@app.route('/register' , methods=['GET','POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    user = User(request.form['username'] , request.form['password'],request.form['email'])
    db.session.add(user)
    db.session.commit()
    flash('User successfully registered')
    return redirect(url_for('login'))

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form['username']
    password = request.form['password']
    remember_me = False
    if 'remember_me' in request.form:
        remember_me = True
    registered_user = User.query.filter_by(username=username).first()
    if registered_user is None:
        flash('Username is invalid' , 'error')
        return redirect(url_for('login'))
    if not registered_user.check_password(password):
        flash('Password is invalid','error')
        return redirect(url_for('login'))
    login_user(registered_user, remember = remember_me)
    flash('Logged in successfully')
    return redirect(request.args.get('next') or url_for('index'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

 
@app.route('/upload_file',methods=['POST'])
@login_required
def upload_file():
    print "Starting file reception"
    _file = request.files['file']
    print _file
#     filename = secure_filename(_file.filename)  # Not securing filenames, since user needs file names to be human-readable
    print pjoin(app.config['UPLOAD_FOLDER'], _file.filename)
    _file.save(pjoin(app.config['UPLOAD_FOLDER'], _file.filename))
    upload = Upload(_file.filename, "example file")
    upload.user = g.user
    db.session.add(upload)
    db.session.commit()
    return "done"

  
  
@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.before_request
def before_request():
    g.user = current_user

    

    
if __name__ == '__main__':
    app.run("0.0.0.0", 4000)
