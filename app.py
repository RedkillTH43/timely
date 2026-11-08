import datetime, os, imghdr, uuid
from flask import Flask, request, render_template, redirect, session, send_from_directory, url_for
from flask_migrate import Migrate
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from sqlalchemy import ForeignKey, MetaData, Table, Column, delete
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from werkzeug.utils import secure_filename

class Base(DeclarativeBase):
  pass

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

association_table = Table(
  "association_table",
  Base.metadata,
  Column("user_id", ForeignKey("users.id"), primary_key=True),
  Column("event.id", ForeignKey("events.id"), primary_key=True)
)

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(model_class=Base, metadata=metadata)
app = Flask("__name__")
migrate = Migrate(app, db, render_as_batch=True)

app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
app.config["UPLOAD_EXTENSIONS"] = [".jpg", ".png"]
app.config["PAYMENT_UPLOAD_PATH"] = "ref_images"
app.config["EVENT_UPLOAD_PATH"] = "event_images"

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"

Session(app)
db.init_app(app)

class User(db.Model):
  __tablename__ = "users"
  id: Mapped[int] = mapped_column(primary_key=True)
  username: Mapped[str] = mapped_column(unique=True, nullable=False)
  password: Mapped[str] = mapped_column(nullable=False)
  role: Mapped[str] = mapped_column(nullable=False)
  events: Mapped[list["Event"]] = relationship(
    secondary=association_table, back_populates="users"
  )
  payments: Mapped[list["Payment"]] = relationship(back_populates="user")

class Event(db.Model):
  __tablename__ = "events"
  id: Mapped[int] = mapped_column(primary_key=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
  users: Mapped[list["User"]] = relationship(
    secondary=association_table, back_populates="events"
  )
  name: Mapped[str] = mapped_column(unique=True, nullable=False)
  venue: Mapped[str] = mapped_column(nullable=False)
  start_date: Mapped[str] = mapped_column(nullable=False)
  end_date: Mapped[str] = mapped_column(nullable=False)
  status: Mapped[str] = mapped_column(nullable=False)
  approval: Mapped[str] = mapped_column(nullable=True)
  description: Mapped[str] = mapped_column(nullable=False)
  amount: Mapped[int] = mapped_column(nullable=True)
  payments: Mapped[list["Payment"]] = relationship(back_populates="event")
  total_registered: Mapped[int] = mapped_column(nullable=True)
  image: Mapped["Image"] = relationship(back_populates="ev_image")
  
class Payment(db.Model):
  __tablename__ = "payments"
  id: Mapped[int] = mapped_column(primary_key=True)
  name: Mapped[str] = mapped_column(nullable=False)
  amount: Mapped[int] = mapped_column(nullable=False)
  acc_name: Mapped[str] = mapped_column(nullable=False)
  acc_number: Mapped[int] = mapped_column(nullable=False)
  ref_number: Mapped[int] = mapped_column(nullable=False)
  date: Mapped[str] = mapped_column(nullable=False)
  status: Mapped[str] = mapped_column(nullable=False)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
  user: Mapped["User"] = relationship(back_populates="payments")
  image: Mapped["Image"] = relationship(back_populates="payment")
  event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=True)
  event: Mapped["Event"] = relationship(back_populates="payments")

class Image(db.Model):
  __tablename__ = "images"
  id: Mapped[int] = mapped_column(primary_key=True)
  name: Mapped[str] = mapped_column(nullable=False)
  file_path: Mapped[str] = mapped_column(nullable=False)
  payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=True)
  payment: Mapped["Payment"] = relationship(back_populates="image")
  event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=True)
  ev_image: Mapped["Event"] = relationship(back_populates="image")
  
class Contact(db.Model):
  __tablename__ = "contacts"
  id: Mapped[int] = mapped_column(primary_key=True)
  name: Mapped[str] = mapped_column(nullable=False)
  email_add: Mapped[str] = mapped_column(nullable=False)
  feedback: Mapped[str] = mapped_column(nullable=False)

with app.app_context():
  db.create_all()

@app.after_request
def after_request(response):
  response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
  response.headers["Expires"] = 0
  response.headers["Pragma"] = "no-cache"
  return response

def login_required(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    if session.get("user_id") is None:
      return redirect("/login")
    return f(*args, **kwargs)
  return decorated_function

@app.route("/")
def index():
  user_id = session.get("user_id")
  users = db.session.execute(db.select(User).order_by(User.username)).scalars()
  events = db.session.execute(db.select(Event).order_by(Event.name)).scalars()
  if not users:
    return redirect("/login")
  elif not events:
    events = []
  current_user = db.session.execute(db.select(User).filter_by(id=user_id)).scalar()
  return render_template("index.html", users=users, events=events, current_user=current_user);
  
@app.route("/signup", methods=["GET", "POST"])
def signup():
  session.clear()
  if request.method == "POST":
    _username = request.form.get("username")
    _password = request.form.get("password")
    _role = request.form.get("role")
    _confirm_pass = request.form.get("confirm_pass")
    if _password != _confirm_pass or not _username or not _password or not _confirm_pass or not _role:
      return redirect("/signup")
    user = User(
      username = _username,
      password = _password,
      role = _role
    )
    db.session.add(user)
    try:
      db.session.commit()
    except:
      return redirect("/signup")
    return redirect("/login")
  else:
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
  session.clear()
  if request.method == "POST":
    _username = request.form.get("username")
    _password = request.form.get("password")
    if not _username or not _password:
      return redirect("/login")
    user = db.session.execute(db.select(User).filter_by(username=_username)).scalar()
    if not user or _password != user.password:
      return redirect("/login")
    session["user_id"] = user.id
    return redirect("/manage")
  else:
    return render_template("login.html")

@app.route("/logout")
def logout():
  session.clear()
  return redirect("/login")

@app.route("/delete_acc")
@login_required
def delete_acc():
  user_id = session.get("user_id")
  user = db.session.execute(db.select(User).filter_by(id=user_id)).scalar()
  if not user or not user_id:
    return redirect("/")
  db.session.delete(user)
  db.session.commit()
  session.clear()
  return redirect("/")

@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
  if request.method == "POST":
    user_id = session.get("user_id")
    user = db.session.execute(db.select(User).filter_by(id=user_id)).scalar()
    _name = request.form.get("ev_name")
    _venue = request.form.get("ev_venue")
    _description = request.form.get("description")
    _amount = request.form.get("amount")
    _image = request.files.get("image")
    
    if not _amount:
      _amount = 0
    start_date_input = request.form.get("start_date")
    end_date_input = request.form.get("end_date")
    _status = "None"
    _approval = "Accepted"
    _total_registered = 0
    if not _name or not _venue or not start_date_input or not end_date_input or not user_id:
      return redirect("/create")
    
    images = db.session.execute(db.select(Image)).scalars()
    
    if secure_filename(_image.filename) in [img.file_path for img in images]:
      unique_str = str(uuid.uuid4())[:8]
      _image.filename = f"{unique_str}_{_image.filename}"
      
    filename = secure_filename(_image.filename)
    if filename != "":
      file_ext = os.path.splitext(filename)[1]
      if file_ext not in app.config["UPLOAD_EXTENSIONS"] or file_ext != validate_image(_image.stream):
        return redirect("/create")
      _image.save(os.path.join(app.config["EVENT_UPLOAD_PATH"], filename))
      
      img = Image(
        name = _name,
        file_path = filename
      )
    
    _start_date = datetime.date.fromisoformat(start_date_input)
    _end_date = datetime.date.fromisoformat(end_date_input)
    if _start_date > datetime.date.today():
      _status = "Upcoming"
    elif _end_date < datetime.date.today():
      _status = "Ended"
    else:
      _status = "Ongoing"
    try:
      event = Event(
        name = _name,
        venue = _venue,
        start_date = _start_date,
        end_date = _end_date,
        status = _status,
        approval = _approval,
        description = _description,
        amount = _amount,
        total_registered = _total_registered,
        image = img
      )
    except:
      return redirect("/create")
    user.events.append(event)
    db.session.add(event)
    db.session.commit()
    return redirect("/events")
  else:
    return render_template("create.html")
    
@app.route("/propose", methods=["GET", "POST"])
@login_required
def propose():
  user_id = session.get("user_id")
  user = db.session.execute(db.select(User).filter_by(id=user_id)).scalar()
  if request.method == "POST":
    today = datetime.date.today()
    _name = request.form.get("ev_name")
    _venue = request.form.get("ev_venue")
    _description = request.form.get("description")
    _amount = request.form.get("amount")
    _image = request.files.get("image")
    if not _amount:
      _amount = 0
    _amount = int(_amount)
    start_date_input = request.form.get("start_date")
    end_date_input = request.form.get("end_date")
    _status = "None"
    _approval = "Pending"
    _total_registered = 0
    if not _name or not _venue or not start_date_input or not end_date_input:
      return redirect("/propose")

    images = db.session.execute(db.select(Image)).scalars()
    
    if secure_filename(_image.filename) in [img.file_path for img in images]:
      unique_str = str(uuid.uuid4())[:8]
      _image.filename = f"{unique_str}_{_image.filename}"
      
    filename = secure_filename(_image.filename)
    if filename != "":
      file_ext = os.path.splitext(filename)[1]
      if file_ext not in app.config["UPLOAD_EXTENSIONS"] or file_ext != validate_image(_image.stream):
        return redirect("/propose")
      _image.save(os.path.join(app.config["EVENT_UPLOAD_PATH"], filename))
      
      img = Image(
        name = _name,
        file_path = filename
      )

    _start_date = datetime.date.fromisoformat(start_date_input)
    _end_date = datetime.date.fromisoformat(end_date_input)
    if _start_date > today and today < _end_date:
      _status = "Upcoming"
    elif _end_date < today and _end_date > _start_date:
      _status = "Ended"
    else:
      _status = "Ongoing"
    try:
      event = Event(
        name = _name,
        venue = _venue,
        start_date = _start_date,
        end_date = _end_date,
        status = _status,
        approval = _approval,
        description = _description,
        amount = _amount,
        total_registered = _total_registered,
        image = img
      )
    except:
      return redirect("/propose")
    user.events.append(event)
    db.session.add(event)
    db.session.commit()
    return redirect("/club_rep_dashboard")
  else:
    proposals = user.events
    return render_template("proposal.html", proposals=proposals)

@app.route("/delete_user/<user_id>")
@login_required
def delete_user(user_id):
  _user_id = user_id
  if not _user_id:
    return redirect("/users")
  user = db.session.execute(db.select(User).filter_by(id=_user_id)).scalar()
  if not user:
    return redirect("/users")
  db.session.delete(user)
  db.session.commit()
  return redirect("/users")

@app.route("/delete_ev/<event_id>")
@login_required
def delete_ev(event_id):
  _event_id = event_id
  event = db.session.execute(db.select(Event).filter_by(id=_event_id)).scalar()
  if not event or not _event_id:
    return redirect("/events")
  db.session.delete(event)
  db.session.commit()
  return redirect("/events")

@app.route("/edit_ev/<event_id>", methods=["GET", "POST"])
@login_required
def edit_ev(event_id):
  if request.method == "POST":
    _event_id = event_id
    _name = request.form.get("ev_name")
    _venue = request.form.get("ev_venue")
    _amount = request.form.get("amount")
    start_date_input = request.form.get("start_date")
    end_date_input = request.form.get("end_date")
    _status = "None"
    if not _name or not _venue or not start_date_input or not end_date_input:
      return redirect(url_for("edit_ev", event_id=_event_id))
    event = db.session.execute(db.select(Event).filter_by(id=event_id)).scalar()
    if not event:
      return redirect(url_for("edit_ev", event_id=_event_id))
    _start_date = datetime.date.fromisoformat(start_date_input)
    _end_date = datetime.date.fromisoformat(end_date_input)
    if _start_date > datetime.date.today():
      _status = "Upcoming"
    elif _end_date < datetime.date.today():
      _status = "Ended"
    else:
      _status = "Ongoing"
    event.name = _name
    event.venue = _venue
    event.start_date = _start_date
    event.end_date = _end_date
    event.status = _status
    event.amount = _amount
    db.session.commit()
    return redirect("/events")
  else:
    try:
      _event_id = event_id
      print(_event_id)
      event = db.session.execute(db.select(Event).filter_by(id=_event_id)).scalar()
      return render_template("edit_ev.html", event=event)
    except:
      return redirect("/events")

@app.route("/edit_user/<user_id>", methods=["POST", "GET"])
@login_required
def edit_user(user_id):
  if request.method == "POST":
    _user_id = user_id
    _name = request.form.get("username")
    _password = request.form.get("pass")
    _role = request.form.get("role")
    if not _name or not _role or not _user_id or not _password:
      print("value error")
      return redirect(url_for("edit_user", user_id=_user_id))
    try:
      user = db.session.execute(db.select(User).filter_by(id=_user_id)).scalar()
    except:
      print("user error")
      return redirect(url_for("edit_user", user_id=_user_id))
    user.username = _name
    user.password = _password
    user.role = _role
    db.session.commit()
    return redirect("/users")
  else:
    try:
      _user_id = user_id
      user = db.session.execute(db.select(User).filter_by(id=_user_id)).scalar()
      return render_template("edit_user.html", user=user)
    except:
      return redirect("/users")

@app.route("/add_user", methods=["GET", "POST"])
@login_required
def add_user():
  if request.method == "POST":
    _username = request.form.get("username")
    _password = request.form.get("password")
    _role = request.form.get("role")
    if not _username or not _password or not _role:
      return redirect("/add_user")
    user = User(
      username = _username,
      password = _password,
      role = _role
    )
    db.session.add(user)
    try:
      db.session.commit()
    except:
      return redirect("/add_user")
    return redirect("/users")
  else:
    return render_template("add_user.html")
      
@app.route("/accept/<event_id>")
@login_required
def accept(event_id):
    _event_id = event_id
    if not _event_id:
      return redirect("/events")
    try:
      event = db.session.execute(db.select(Event).filter_by(id=_event_id)).scalar()
    except:
      return redirect("/events")
    event.approval = "Accepted"
    db.session.commit()
    return redirect("/events")

@app.route("/decline/<event_id>")
@login_required
def decline(event_id):
    _event_id = event_id
    if not _event_id:
      return redirect("/events")
    try:
      event = db.session.execute(db.select(Event).filter_by(id=_event_id)).scalar()
    except:
      return redirect("/events")
    event.approval = "Declined"
    db.session.commit()
    return redirect("/events")

@app.route("/accept_pay/<pay_id>")
@login_required
def accept_pay(pay_id):
    _pay_id = pay_id
    if not _pay_id:
      return redirect("/payments")
    try:
      payment = db.session.execute(db.select(Payment).filter_by(id=_pay_id)).scalar()
    except:
      return redirect("/payments")
    payment.status = "Paid"
    db.session.commit()
    return redirect("/payments")

@app.route("/decline_pay/<pay_id>")
@login_required
def decline_pay(pay_id):
    _pay_id = pay_id
    if not _pay_id:
      return redirect("/payments")
    try:
      payment = db.session.execute(db.select(Payment).filter_by(id=_pay_id)).scalar()
    except:
      return redirect("/payments")
    payment.status = "Cancelled"
    db.session.commit()
    return redirect("/payments")

@app.route("/delete_pay/<pay_id>")
@login_required
def delete_pay(pay_id):
  _pay_id = pay_id
  payment = db.session.execute(db.select(Payment).filter_by(id=_pay_id)).scalar()
  image = payment.image
  if not _pay_id or not payment or not image:
    return redirect("/payments")
  try:
    os.remove(os.path.join(app.config["UPLOAD_PATH"], image.file_path))
  except:
    pass
  db.session.delete(image)
  db.session.delete(payment)
  db.session.commit()
  return redirect("/payments")

@app.route("/join", methods=["POST"])
@login_required
def join():
  if request.method == "POST":
    user_id = session.get("user_id")
    event_id = request.form.get("event_id")
    if not event_id or not user_id:
      return redirect("/")
    user = db.session.execute(db.select(User).filter_by(id=user_id)).scalar()
    event = db.session.execute(db.select(Event).filter_by(id=event_id)).scalar()
    if not user or not event:
      return redirect("/")
    if event.amount:
      return redirect(url_for('pay', event_id=event.id))
    user.events.append(event)
    event.total_registered += 1
    try:
      db.session.commit()
    except:
      return redirect("/")
    return redirect("/my_events")
  
@app.route("/cancel", methods=["POST"])
@login_required
def cancel():
  if request.method == "POST":
    user_id = session.get("user_id")
    event_id = request.form.get("event_id")
    if not event_id or not user_id:
      return redirect("/")
    user = db.session.execute(db.select(User).filter_by(id=user_id)).scalar()
    event = db.session.execute(db.select(Event).filter_by(id=event_id)).scalar()
    if not user or not event:
      return redirect("/")
    user.events.remove(event)
    db.session.commit()
    return redirect("/my_events")
  
@app.route("/reports")
@login_required
def reports():
  total_student = 0
  total_alumni = 0
  student_amount = 0
  alumni_amount = 0
  events = db.session.execute(db.select(Event).order_by(Event.total_registered.desc()).limit(5)).scalars()
  students = db.session.execute(db.select(User).filter_by(role="student")).scalars()
  alumni = db.session.execute(db.select(User).filter_by(role="alumni")).scalars()
  for student in students:
    if student.events:
      for event in student.events:
        student_amount += event.amount
        total_student += 1
  for alumnus in alumni:
    if alumnus.events:
      for event in alumnus.events:
        alumni_amount += event.amount
        total_alumni += 1
  registered_num = total_student + total_alumni
  event_num = db.session.execute(db.func.count(Event.id)).scalar()
  amount_num = db.session.execute(db.func.sum(Event.amount)).scalar()
  if not amount_num:
    amount_num = 0
  if not event_num:
    event_num = 0
  report = {
    "top5_ev": events,
    "alumni": [total_alumni, alumni_amount],
    "student": [total_student, student_amount],
    "total_registered": registered_num,
    "total_event": event_num,
    "total_amount": amount_num,
  }
  return render_template("reports.html", report=report)

@app.route("/manage")
def manage():
  try:
    user_id = session.get("user_id")
    user = db.session.execute(db.select(User).filter_by(id=user_id)).scalar()
  except:
    return redirect("/login")
  if user.role == "admin":
    return redirect("/admin_dashboard")
  elif user.role == "club_rep":
    return redirect("/club_rep_dashboard")
  else:
    return redirect("/")

@app.route("/club_rep_dashboard")
@login_required
def club_rep_dashboard():
  user_id = session.get("user_id")
  current_user = db.session.execute(db.select(User).filter_by(id=user_id)).scalar()
  total_accepted = 0
  total_pending = 0
  total_declined = 0
  total_proposal = len(current_user.events)
  events = current_user.events
  for event in events:
    if event.approval == "Accepted":
      total_accepted += 1
    elif event.approval == "Pending":
      total_pending += 1
    else:
      total_declined += 1
  return render_template("club_rep_dashboard.html", total_accepted=total_accepted, total_pending=total_pending, total_declined=total_declined, total_proposal=total_proposal, events=events)

@app.route("/admin_dashboard")
@login_required
def admin_dashboard():
  total_proposal = 0
  users = db.session.execute(db.select(User).filter_by(role="club_rep")).scalars();
  for user in users:
    for proposal in user.events:
      total_proposal += 1
  events = db.session.execute(db.select(Event).filter_by(status="Ongoing", approval="Accepted")).scalars()
  total_event = db.session.execute(db.func.count(Event.id)).scalar()
  total_user = db.session.execute(db.func.count(User.id)).scalar()
  return render_template("admin_dashboard.html", total_event=total_event, total_user=total_user, events=events, total_proposal=total_proposal)

@app.route("/events")
@login_required
def events():
  events = db.session.execute(db.select(Event).order_by(Event.approval)).scalars()
  return render_template("events.html", events=events)

@app.route("/users")
@login_required
def users():
  users = db.session.execute(db.select(User).order_by(User.id)).scalars()
  return render_template("users.html", users=users)

@app.route("/payments")
@login_required
def payments():
  payments = db.session.execute(db.select(Payment).order_by(Payment.id)).scalars()
  images = db.session.execute(db.select(Image).order_by(Image.id)).scalars()
  return render_template("payments.html", payments=payments, images=images)

@app.route("/pay/<event_id>", methods=["GET", "POST"])
@login_required
def pay(event_id):
  if request.method == "POST":
    _user_id = session.get("user_id")
    current_user = db.session.execute(db.select(User).filter_by(id=_user_id)).scalar()
    _event_id = event_id
    _acc_name = request.form.get("acc_name")
    _acc_number = request.form.get("acc_number")
    _amount = request.form.get("amount")
    _ref_number = request.form.get("ref_number")
    _image = request.files.get("image")
    _date = datetime.datetime.now()
    _status = "Processing"
    event = db.session.execute(db.select(Event).filter_by(id=_event_id)).scalar()
    event_name = f"Payment for {event.name}"
    images = db.session.execute(db.select(Image)).scalars()
    
    if not _event_id or not _acc_name or not _acc_number or not _amount or not _image or not event_name:
      return redirect("/pay")
    
    if secure_filename(_image.filename) in [img.file_path for img in images]:
      unique_str = str(uuid.uuid4())[:8]
      _image.filename = f"{unique_str}_{_image.filename}"
      
    filename = secure_filename(_image.filename)
    if filename != "":
      file_ext = os.path.splitext(filename)[1]
      if file_ext not in app.config["UPLOAD_EXTENSIONS"] or file_ext != validate_image(_image.stream):
        return redirect("/pay")
      _image.save(os.path.join(app.config["PAYMENT_UPLOAD_PATH"], filename))
      
      img = Image(
        name = event_name,
        file_path = filename
      )
      
      payment = Payment(
        name = event_name,
        acc_name = _acc_name,
        acc_number = _acc_number,
        amount = _amount,
        ref_number = _ref_number,
        date = _date,
        status = _status,
        image = img,
        user_id = _user_id
      )
      event.payments.append(payment)
      current_user.payments.append(payment)
      current_user.events.append(event)
      db.session.add_all([img, payment])
      db.session.commit()
    return redirect("/my_events")
  else:
    event = db.session.execute(db.select(Event).filter_by(id=event_id)).scalar()
    return render_template("pay.html", event=event)

@app.route("/ref_images/<filename>")
def ref_images(filename):
  return send_from_directory(app.config["PAYMENT_UPLOAD_PATH"], filename)

def validate_image(stream):
  header = stream.read(512)
  stream.seek(0)
  format = imghdr.what(None, header)
  if not format:
    return None
  return "." + (format if format != "jpeg" else "jpg")
  
@app.route("/reset_db")
@login_required
def reset_db():
  for table in db.metadata.tables.values():
    db.session.execute(delete(table))
  db.session.commit()
  return redirect("/")

@app.route("/admin_settings")
@login_required
def admin_settings():
  return render_template("admin_settings.html")
  
@app.route("/club_rep_settings")
@login_required
def club_rep_settings():
  return render_template("club_rep_settings.html")

@app.route("/settings")
@login_required
def settings():
  return render_template("settings.html")

@app.route("/my_events")
@login_required
def my_events():
  user_id = session.get("user_id")
  current_user = db.session.execute(db.select(User).filter_by(id=user_id)).scalar()
  return render_template("my_events.html", current_user=current_user)

@app.route("/current_events")
def current_events():
  user_id = session.get("user_id")
  current_user = db.session.execute(db.select(User).filter_by(id=user_id)).scalar()
  events = db.session.execute(db.select(Event).filter_by(approval="Accepted").order_by(Event.id)).scalars()
  return render_template("current_events.html", events=events, current_user=current_user)
  
@app.route("/about")
def about():
  user_id = session.get("user_id")
  current_user = db.session.execute(db.select(User).filter_by(id=user_id)).scalar()
  return render_template("about.html", current_user=current_user)
  
@app.route("/contact", methods=["GET", "POST"])
def contact():
  if request.method == "POST":
    _name = request.form.get("name")
    if not _name:
      _name = "Anonymous"
    _email_add = request.form.get("email_add")
    _feedback = request.form.get("feedback")
    if not _email_add or not _feedback:
      return redirect("/contact")
    contact = Contact(
      name = _name,
      email_add = _email_add,
      feedback = _feedback
    )
    try:
      db.session.add(contact)
    except:
      return redirect("/contact")
    db.session.commit()
    return redirect("/")
  else:
    user_id = session.get("user_id")
    current_user = db.session.execute(db.select(User).filter_by(id=user_id)).scalar()
    return render_template("contact.html", current_user=current_user)
    
@app.route("/feedbacks")
@login_required
def feedbacks():
  feedbacks = db.session.execute(db.select(Contact).order_by(Contact.id)).scalars()
  return render_template("feedbacks.html", feedbacks=feedbacks)
  
@app.route("/delete_feedback/<feedback_id>")
@login_required
def delete_feedback(feedback_id):
  _feedback_id = feedback_id
  feedback = db.session.execute(db.select(Contact).filter_by(id=_feedback_id)).scalar()
  if not feedback:
    return redirect("/feedbacks")
  db.session.delete(feedback)
  try:
    db.session.commit()
  except:
    return redirect("/feedbacks")
  return redirect("/feedbacks")

@app.route("/register/<event_id>")
def register(event_id):
  event = db.session.execute(db.select(Event).filter_by(id=event_id)).scalar()
  return render_template("register.html", event=event)

@app.route("/event_images/<event_id>")
def event_images(event_id):
  event = db.session.execute(db.select(Event).filter_by(id=event_id)).scalar()
  filename = event.image.file_path
  return send_from_directory(app.config["EVENT_UPLOAD_PATH"], filename)