import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime
import pytz
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests

from helpers import login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

scopes = 'https://www.googleapis.com/auth/calendar'
# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def _force_https():
    # my local dev is set on debug, but on AWS it's not (obviously)
    # I don't need HTTPS on local, change this to whatever condition you want.
    if not app.debug:
        from flask import _request_ctx_stack
        if _request_ctx_stack is not None:
            reqctx = _request_ctx_stack.top
            reqctx.url_adapter.url_scheme = 'https'

app.before_request(_force_https)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


""" Dropdowns """

###----- Update booking form dropdowns ----->
@app.route('/_booking_dropdown')
@login_required
def booking_dropdown():

    # The value of the department dropdown (selected by the user)
    selected_dept = request.args.get('selected_dept', type=str)

    # Get values for type and item dropdown
    updated_types = get_dropdown_values()[selected_dept]
    updated_items = get_item_dropdown_values(updated_types[0])[updated_types[0]]

    # Convert dropdown values to html string
    html_string_selected = ''
    for type in updated_types:
        html_string_selected += '<option value="{}">{}</option>'.format(type, type)
    html_string_selected_item = ''
    for item in updated_items:
        html_string_selected_item += '<option value="{}">{}</option>'.format(item, item)

    return jsonify(html_string_selected=html_string_selected, html_string_selected_item=html_string_selected_item)

@app.route('/_booking_item_dropdown')
@login_required
def booking_item_dropdown():

    # The value of type dropdown (selected by the user)
    selected_type = request.args.get('selected_type', type=str)
    # Get values for item dropdown
    updated_items = get_item_dropdown_values(selected_type)[selected_type]
    # Convert dropdown values to html string
    html_string_selected = ''
    for item in updated_items:
        html_string_selected += '<option value="{}">{}</option>'.format(item, item)

    return jsonify(html_string_selected=html_string_selected)

###----- Populate dropdowns ----->
def get_dropdown_values():

    #----- Get departments ----->
    d = db.execute("SELECT dept FROM kit").fetchall()
    deptlist = []
    # Delete duplicates
    for i in range(0, len(d)):
        if d[i] not in d[i+1:]:
            deptlist.append(d[i])

    dept_type_relations = {}

    #---- Get types ----->
    for dept in deptlist:
        # Get department from list
        dept = dept['dept']
        # Create list of types
        typelist = []
        # Get types
        t = db.execute("SELECT type FROM kit WHERE dept = :dept", {"dept": dept}).fetchall()
        # Delete duplicates
        for i in range(0, len(t)):
            if t[i] not in t[i+1:]:
                typelist.append(t[i])

        #----- Create dept/type dictionary ----->
        for item in typelist:
            type = item['type']
            if dept in dept_type_relations:
                # Append the new type to the existing array at this slot
                dept_type_relations[dept].append(type)
            else:
                # Create a new array in this slot
                dept_type_relations[dept] = [type]

    return dept_type_relations

def get_item_dropdown_values(type):

    type_item_relations = {}

    #----- Get items ----->
    type = type
    # get dept to control for shared department types (i.e. lighting and sound both have a "control" type)
    dept = request.args.get('selected_dept', type=str)
    # if change initiated from the type selector, dept argument will not be supplied
    if not dept:
        it = db.execute("SELECT item FROM kit WHERE type = :type", {"type": type}).fetchall()
    else:
        it = db.execute("SELECT item FROM kit WHERE type = :type AND dept = :dept", {"type": type, "dept": dept}).fetchall()
    #create list of items
    itemlist = []
    # delete duplicates
    for i in range(0, len(it)):
        if it[i] not in it[i+1:]:
            itemlist.append(it[i])

    #----- Create type/item dictionary ----->
    for item in itemlist:
        item = item['item']
        if type in type_item_relations:
            # append the new item to the existing array at this slot
            type_item_relations[type].append(item)
        else:
            # create a new array in this slot
            type_item_relations[type] = [item]

    return type_item_relations

###----- Update add item form dropdowns ----->
@app.route('/_update_dropdown')
@login_required
def update_dropdown():

    # the value of the department dropdown (selected by the user)
    selected_dept = request.args.get('selected_dept', type=str)

    # get values for the type dropdown
    updated_types = get_dropdown_values()[selected_dept]
    updated_items = get_item_dropdown_values(updated_types[0])[updated_types[0]]
    updated_types.append("Add New")
    updated_items.append("Add New")
    # create the values in the dropdown as an html string
    html_string_selected = ''
    for type in updated_types:
        html_string_selected += '<option value="{}">{}</option>'.format(type, type)
    html_string_selected_item = ''
    for item in updated_items:
        html_string_selected_item += '<option value="{}">{}</option>'.format(item, item)

    return jsonify(html_string_selected=html_string_selected, html_string_selected_item=html_string_selected_item)

@app.route('/_update_item_dropdown')
@login_required
def update_item_dropdown():

    # the value of the type dropdown (selected by the user)
    selected_type = request.args.get('selected_type', type=str)
    if selected_type == "Add New":
        updated_items = ["Add New"]
    else:
        # get values for the item dropdown
        updated_items = get_item_dropdown_values(selected_type)[selected_type]
        updated_items.append("Add New")
        # create the values in the dropdown as an html string
    html_string_selected = ''
    for item in updated_items:
        html_string_selected += '<option value="{}">{}</option>'.format(item, item)

    return jsonify(html_string_selected=html_string_selected)


""" Assets """

###----- Equipment list ----->
@app.route("/", methods=["GET", "POST"])
@login_required
def index():


    if request.method == "POST":

        #----- Search Query ----->
        if request.form.get("search"):

            search = request.form.get("search")
            # Add wildcard for database call
            search = f"%{search}%"

            # Search equipment for query
            kit = db.execute("SELECT * FROM kit WHERE dept ILIKE :search OR type ILIKE :search OR item ILIKE :search OR venue ILIKE :search ORDER BY type, item ASC", {"search": search}).fetchall()

            # Redirect user to home page
            if not kit:
                flash('No items found')
                return redirect("/")
            else:
                    #----- add item dropdown values ----->
                    # Get venue list for dropdown
                    venue = db.execute("SELECT * FROM venue").fetchall()
                    # Jinja venue select
                    venueselect = "Select..."

                    # Get deparment/types dictionary
                    dept_type_relations = get_dropdown_values()

                    # First entry in dept/type dictionary
                    default_depts = sorted(dept_type_relations.keys())
                    # Associated types for first dept entry
                    default_types = dept_type_relations[default_depts[0]]
                    # Associated items for first type entry
                    type_item_relations = get_item_dropdown_values(default_types[0])
                    # First entry in type/item dictionary
                    default_items = type_item_relations[default_types[0]]
                    # Add "Add New" to dropdown options
                    default_types.append("Add New")
                    default_items.append("Add New")

                    return render_template('index.html',
                                           all_depts=default_depts,
                                           all_types=default_types,
                                           all_items=default_items,
                                           venue=venue,
                                           venueselect=venueselect,
                                           kit=kit)


    else:

        #----- Equipment List ----->
        # Ordered dictionary of kit
        kit = db.execute("SELECT * FROM kit ORDER BY id DESC").fetchall()

        #----- Add item dropdown values ----->
        # Get venue list for dropdown
        venue = db.execute("SELECT * FROM venue").fetchall()
        # Jinja venue select
        venueselect = "Select..."

        # Get deparment/types dictionary
        dept_type_relations = get_dropdown_values()

        # First entry in dept/type dictionary
        default_depts = sorted(dept_type_relations.keys())
        # Associated types for first dept entry
        default_types = dept_type_relations[default_depts[0]]
        # Associated items for first type entry
        type_item_relations = get_item_dropdown_values(default_types[0])
        # First entry in type/item dictionary
        default_items = type_item_relations[default_types[0]]
        # Add "Add New" to dropdown options
        default_types.append("Add New")
        default_items.append("Add New")

        return render_template('index.html',
                               all_depts=default_depts,
                               all_types=default_types,
                               all_items=default_items,
                               venue=venue,
                               venueselect=venueselect,
                               kit=kit)

###----- Asset info ----->
@app.route("/asset/<id>", methods=["GET", "POST"])
@login_required
def asset(id):

    # Venue dropdown
    venueselect = "Select..."
    venue = db.execute("SELECT * FROM venue").fetchall()

    # Get item from id
    # id returned as input from asset url
    itemid = id
    i = db.execute("SELECT item FROM kit WHERE id = :id", {"id": itemid}).fetchall()
    item = i[0]['item']

    # Count of item in stock (1 of c)
    c = db.execute("SELECT COUNT( * ) FROM kit WHERE item = :item", {"item": item}).fetchall()
    count = c[0][0]

    #Get notes
    notes = db.execute("SELECT id, notes, noteadded FROM notes WHERE itemid = :id ORDER BY id DESC", {"id": itemid}).fetchall()

    #Get today
    today = datetime.today().strftime('%Y-%m-%d')
    #Get item bookings
    assbook = db.execute("SELECT id, quantity, item, start, endtime, event, venue FROM bookings WHERE endtime >= :today AND item = :item", {"item": item, "today": today}).fetchall()

    #hide booking table if none
    if not assbook:
        hide = 'hidden'
    else:
        hide = ''

    #----- Add Note ----->
    if request.method == "POST":

        #----- Delete Note ----->
        if request.form.get("delete"):
            delete = request.form.get("delete")
            db.execute("DELETE FROM notes WHERE id = :id", {"id": delete})
            db.commit()

            return redirect(url_for('asset', id=itemid))

        #----- Add Note ----->
        if request.form.get("note"):
            note = request.form.get("note")

            #Get today
            noteadded = datetime.today().strftime('%Y-%m-%d')

            #Add to notes table
            db.execute("INSERT INTO notes (itemid, notes, item, noteadded) VALUES (:itemid, :notes, :item, :noteadded)",
            {"itemid": itemid,
            "notes": note,
            "item": item,
            "noteadded": noteadded})
            db.commit()

            #Return to asset page
            return redirect(url_for('asset', id=itemid))
    else:

        return render_template("asset.html", notes = notes, item = item, count = count, venue = venue, itemid=itemid, venueselect=venueselect, assbook=assbook, hide=hide)

###----- Add Asset ----->
@app.route("/add", methods=["GET", "POST"])
@login_required
def add():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Get department
        dept = request.form.get("dept")

        # If input from new type form - override type dropdown
        if request.form.get("newtype"):
            type = request.form.get("newtype")
        else:
            type = request.form.get("type")

        # If input from new item form - override item dropdown
        if request.form.get("newitem"):
            item = request.form.get("newitem")
        else:
            item = request.form.get("item")
            item = item

        # Get venue
        venue = request.form.get("venue")
        # Get quantity
        total = request.form.get("howmany")

        # Error checking
        if not dept:
            flash("Please select department")
            return redirect("/")
        if not type or type == "Add New...":
            flash("Please select type")
            return redirect("/")
        if item == "Select..." or item == "Add New...":
            flash("Please select item")
            return redirect("/")
        if venue == "Select...":
            flash("Please select venue")
            return redirect("/")
        if total.isnumeric() == False:
            flash("Please enter quantity")
            return redirect("/")

        # Add item to assets
        for i in range(int(total)):
            db.execute("INSERT INTO kit (dept, type, item, venue) VALUES(:dept, :type, :item, :venue)",
            {"dept": dept,
            "type": type,
            "item": item,
            "venue": venue})
            db.commit()

        # Date added
        added = datetime.today().strftime('%Y-%m-%d')
        notes = f"Added {added}"

        # Get id and item from latest addition to assets
        i = db.execute("SELECT id, item FROM kit ORDER BY id DESC").fetchone()
        newid = i['id']
        newitem = i['item']

        # Add note of asset addition
        db.execute("INSERT INTO notes (itemid, notes, item, noteadded) VALUES (:itemid, :notes, :item, :noteadded)",
        {"itemid": newid,
        "notes": notes,
        "item": newitem,
        "noteadded": added})
        db.commit()

        # Redirect user to home page
        return redirect("/")

###----- Delete Asset ----->
@app.route("/deleteitem/<id>", methods=["POST"])
@login_required
def deleteitem(id):


    id=id
    #----- Delete item from bookings table ----->
    db.execute("DELETE FROM kit WHERE id = :id", {"id": id})
    db.commit()

    return redirect("/")


""" Bookings """

@app.route("/addbooking", methods=["GET", "POST"])
@login_required
def addbooking():

    #----- Get booking form input ----->
    id = session["user_id"]
    b = db.execute("SELECT username FROM users WHERE id = :id", {"id": id}).fetchall()
    user= b[0]['username']
    # Hidden id form input for redirect back to booking page - from "itemid" jinja
    id = request.form.get("id")
    # Get department item - type not used, but needed for dropdown dependencies
    dept = request.form.get("dept")
    type = request.form.get("type")
    item = request.form.get("item")
    # Booking dates
    start = request.form.get("start")
    end = request.form.get("end")
    # Event and location
    event = request.form.get("event")
    venue = request.form.get("venue")
    # Booker
    booker = user
    # Quantity
    quantity = request.form.get("howmany")
    # Today
    added = 'now'

    #----- Error Checking ----->
    # If dept not supplied - route reached from asset.html
    if not dept:
        d = db.execute("SELECT dept FROM kit WHERE id = :id", {"id": id}).fetchone()
        dept=d['dept']
        print(dept)
        if not item:
            flash("Please select item")
            return redirect(url_for('asset', id=id))
        if quantity.isnumeric() == False:
            flash("Please enter quantity")
            return redirect(url_for('asset', id=id))
        if venue == "Select...":
            flash("Please select venue")
            return redirect(url_for('asset', id=id))
        if not event:
            flash("Please enter event")
            return redirect(url_for('asset', id=id))
        if not booker:
            flash("Please enter booker")
            return redirect(url_for('asset', id=id))
        if start > end:
            flash("End date before start date")
            return redirect(url_for('asset', id=id))

    # Route reached from booking.html
    if not item:
        flash("Please select item")
        return redirect("/booking")
    if quantity.isnumeric() == False:
        flash("Please enter quantity")
        return redirect("/booking")
    if venue == "Select...":
        flash("Please select venue")
        return redirect("/booking")
    if not event:
        flash("Please enter event")
        return redirect("/booking")
    if not booker:
        flash("Please enter booker")
        return redirect("/booking")
    if start > end:
        flash("End date before start date")
        return redirect("/booking")
    # Check stock count
    c = db.execute("SELECT COUNT( * ) FROM kit WHERE item = :item", {"item": item}).fetchall()
    count = c[0][0]
    count = int(count)
    # Check count of item alread booked
    quant = db.execute("SELECT quantity FROM bookings WHERE start BETWEEN :start AND :end OR endtime BETWEEN :start AND :end AND item = :item", {"item": item, "start": start, "end": end}).fetchall()
    # Initiallize variable, q to count items booked
    q = 0
    for row in quant:
        q = q + row['quantity']

    # Check count available against quantity requested
    if count < q or count < int(quantity):
        flash('Assets unavailable')
        return redirect("/booking")

    #----- Add booking to bookings table ----->
    db.execute("INSERT INTO bookings (dept, item, venue, event, start, endtime, booker, quantity, added) VALUES(:dept, :item, :venue, :event, :start, :end, :booker, :quantity, :added)",
    {"dept": dept,
    "item": item,
    "venue": venue,
    "event": event,
    "start": start,
    "end": end,
    "booker": booker,
    "quantity": quantity,
    "added": added})
    db.commit()

    #----- Add booking note ----->
    # Today
    added = datetime.today().strftime('%Y-%m-%d')
    # Get new booking id
    i = db.execute("SELECT id from bookings ORDER BY id DESC").fetchone()
    bookid=i['id']
    # Note fstring
    notes = f"Added {added}"
    # Add note of booking addition
    db.execute("INSERT INTO bookingnotes (bookingid, notes, noteadded) VALUES (:bookingid, :notes, :noteadded)",
    {"bookingid": bookid,
    "notes": notes,
    "noteadded": added})
    db.commit()

    # Redirect user to booking page
    return redirect("/booking")


###---- Booking list and add booking ----->
@app.route("/booking", methods=["GET", "POST"])
@login_required
def booking():

    if request.method == "POST":
        #----- Filter Bookings ----->
        if request.form.get("search"):
            type = dept = item = venueselect = "Select..."
            venue = db.execute("SELECT * FROM venue").fetchall()

            # Get search
            search = request.form.get("search")
            # Add wildcard for database call
            search = f"%{search}%"

            bookings = db.execute("SELECT id, quantity, item, start, endtime, event, venue FROM bookings WHERE dept ILIKE :search OR item ILIKE :search OR venue ILIKE :search OR booker ILIKE :search OR event ILIKE :search ORDER BY start DESC", {"search": search}).fetchall()
            # Redirect user to home page
            if not bookings:
                # Redirect user to home page
                flash('No items found')
                return redirect("/booking")

            else:
                # Venue list for dropdown
                venue = db.execute("SELECT * FROM venue").fetchall()
                # Jinja venue select
                venueselect = "Select..."

                #----- Add booking dropdown values ----->
                # Get deparment/types dictionary
                dept_type_relations = get_dropdown_values()
                # First entry in dept/type dictionary
                default_depts = sorted(dept_type_relations.keys())
                # Associated types for first dept entry
                default_types = dept_type_relations[default_depts[0]]
                # Associated items for first type entry
                type_item_relations = get_item_dropdown_values(default_types[0])
                # First entry in type/item dictionary
                default_items = type_item_relations[default_types[0]]

                return render_template('booking.html',
                                       all_depts=default_depts,
                                       all_types=default_types,
                                       all_items=default_items,
                                       venue=venue,
                                       venueselect=venueselect,
                                       bookings=bookings)

    else:

        #----- Booking List ----->
        # Ordered dictionary of bookings
        bookings = db.execute("SELECT id, quantity, item, start, endtime, event, venue FROM bookings ORDER BY id DESC").fetchall()
        # Get venue list for dropdown
        venue = db.execute("SELECT * FROM venue").fetchall()
        # Jinja venue select
        venueselect = "Select..."

        #----- Add booking dropdown values ----->
        # Get deparment/types dictionary
        dept_type_relations = get_dropdown_values()
        # First entry in dept/type dictionary
        default_depts = sorted(dept_type_relations.keys())
        # Associated types for first dept entry
        default_types = dept_type_relations[default_depts[0]]
        # Associated items for first type entry
        type_item_relations = get_item_dropdown_values(default_types[0])
        # First entry in type/item dictionary
        default_items = type_item_relations[default_types[0]]

        return render_template('booking.html',
                               all_depts=default_depts,
                               all_types=default_types,
                               all_items=default_items,
                               venue=venue,
                               venueselect=venueselect,
                               bookings=bookings)

###----- Booking info ----->
@app.route("/bookinginfo/<id>", methods=["GET", "POST"])
@login_required
def bookinginfo(id):

    # id returned as input from booking url
    bookid = id

    if request.method == "POST":
        #----- Delete Note ----->
        if request.form.get("delete"):
            delete = request.form.get("delete")
            db.execute("DELETE FROM bookingnotes WHERE id = :id", {"id": delete})
            db.commit()

            return redirect(url_for('bookinginfo', id=bookid))

        #----- Add Note ----->
        if request.form.get("note"):
            # Get new note
            note = request.form.get("note")
            # Get today
            noteadded = datetime.today().strftime('%Y-%m-%d')
            # Add note to bookingnotes table
            db.execute("INSERT INTO bookingnotes (bookingid, notes, noteadded) VALUES (:bookingid, :notes, :noteadded)",
            {"bookingid": bookid,
            "notes": note,
            "noteadded": noteadded})
            db.commit()

            # Redirect user to booking page
            return redirect(url_for('bookinginfo', id=bookid))

        #----- Get booking update form input ----->
        # Get department item - type not used, but needed for dropdown dependencies
        dept = request.form.get("dept")
        type = request.form.get("type")
        item = request.form.get("item")
        # Booking dates
        start = request.form.get("start")
        end = request.form.get("end")
        # Venue and event
        venue = request.form.get("venue")
        event = request.form.get("event")
        # Booker
        booker = request.form.get("booker")
        # Quantity
        quantity = request.form.get("howmany")

        #----- Error Checking ----->
        if not item:
            flash("Please select item")
            return redirect(url_for('bookinginfo', id=bookid))
        if quantity.isnumeric() == False:
            flash("Please enter quantity")
            return redirect(url_for('bookinginfo', id=bookid))
        if venue == "Select...":
            flash("Please select venue")
            return redirect(url_for('bookinginfo', id=bookid))
        if not event:
            flash("Please enter event")
            return redirect(url_for('bookinginfo', id=bookid))
        if not booker:
            flash("Please enter booker")
            return redirect(url_for('bookinginfo', id=bookid))
        if start > end:
            flash("End date before start date")
            return redirect(url_for('bookinginfo', id=bookid))

        # Update booking in bookings table
        db.execute("UPDATE bookings SET item = :item , venue = :venue, event = :event, start = :start, endtime = :end, booker = :booker, quantity = :quantity WHERE id = :id",
        {"id": bookid,
        "item": item,
        "venue": venue,
        "event": event,
        "start": start,
        "end": end,
        "booker": booker,
        "quantity": quantity})
        db.commit()

        flash("Booking Updated")
        # Redirect user to booking page
        return redirect(url_for('bookinginfo', id=bookid))

    #----- Booking info ----->
    bookid = id
    # Get notes list
    notes = db.execute("SELECT  id, notes, noteadded FROM bookingnotes WHERE bookingid = :id ORDER BY id DESC", {"id": bookid}).fetchall()
    # Get booking info
    booking = db.execute("SELECT * FROM Bookings WHERE id = :id", {"id": bookid}).fetchone()

    #----- Update booking dropdown values ----->
    # Department in dictionary format for dropdown function
    dept = {booking["dept"]: "foo"}
    # Get item
    item = booking["item"]
    item=item
    # Get type
    t = db.execute("SELECT type FROM kit WHERE item = :item", {"item": item}).fetchone()
    # Type in dictionary format for dropdown function
    type = {t["type"]:"foo"}
    # Item in dictionary format for dropdown function
    item = {item: "foo"}
    # Booking values for update booking form
    venue = db.execute("SELECT * FROM venue").fetchall()
    venueselect = booking["venue"]
    event = booking["event"]
    booker = booking["booker"]
    quantity = booking["quantity"]
    # Booking values specified
    default_depts = dept
    default_types = type
    default_items = item

    #Get booking times
    time = db.execute("SELECT start, endtime FROM bookings WHERE id = :id", {"id": bookid}).fetchone()
    start = time['start']
    end = time['endtime']
    startdate = start.date()
    print(startdate)
    starttime = start.time()
    print(starttime)
    enddate = end.date()
    print(enddate)
    endtime = end.time()
    print(endtime)
    return render_template('bookinginfo.html',
                           all_depts=default_depts,
                           all_types=default_types,
                           all_items=default_items,
                           bookid=bookid, notes=notes,
                           booking=booking,
                           venueselect=venueselect,
                           venue=venue, item=item,
                           event=event, quantity=quantity, booker=booker,
                           starttime=starttime, startdate=startdate,
                           endtime=endtime, enddate=enddate,
                           start=start, end=end)

###----- Calendar Events ----->
@app.route("/calendar", methods=["GET", "POST"])
@login_required
def calendar():
    #initiallize event list
    events = []

    # Get booking list
    bookings = db.execute("SELECT * FROM bookings").fetchall()
    for booking in bookings:
        # Values for event json for Fullcalendar
        id = booking['id']
        url = f"https://morning-shore-34495.herokuapp.com/bookinginfo/{id}"
        item = booking['item']
        quantity = booking['quantity']
        dept = booking['dept']
        ev = booking['event']
        venue = booking['venue']
        booker = booking['booker']
        # Calendar booking colours
        if dept == "Sound":
            color = 'lightseagreen'
        if dept == "Lighting":
            color = '#537fbe'
        if dept == "AV":
            color = 'mediumpurple'
        # Dates in datetime string like '2020-05-28T09:00:00-07:00'
        startdate = (booking['start']).strftime("%Y-%m-%dT%H:%M:%S")
        enddate = (booking['endtime']).strftime("%Y-%m-%dT%H:%M:%S")

        #json event in Fullcalendar format
        event = {
          'title': f"{quantity} x {item}(s) for {ev}",
          'start': startdate,
          'end': enddate,
          'url': url,
          'color': color,

          'extendedProps': {
          'quantity': quantity,
          'department': dept,
          'event': ev,
          'venue': venue,
          'booker': booker
          }
          }
        events.append(event)


    #----- Theatre YesPlan Events ---->
    #Get json from Yesplan API
    yes = requests.get("https://horsecross.yesplan.be/api/events/location%3Apt%20date%3A%23next8months?api_key=5C76336690A5BFB115651E1D97CD4262")
    # Get dicionary of events
    data = yes.json()
    yesbooking = data['data']

    # Values for json event for Fullcalendar
    for booking in yesbooking:

        if booking['group'] == None:
            name = "no event title"
        else:
            name = booking['group']['name']
        location = booking['locations'][0]['name']
        evstart = booking['starttime']
        evend = booking['endtime']

        # make json event
        yesevent = {
          'title': f"{name} ({location})",
          'start': evstart,
          'end': evend,
          'url': "https://horsecross.yesplan.be/Yesplan",
          'color': "pink"
          }
        # add to events list
        events.append(yesevent)

    #----- Studio YesPlan Events ---->
    #Get json from Yesplan API
    yes = requests.get("https://horsecross.yesplan.be/api/events/location%3Astudio%20date%3A%23next8months?api_key=5C76336690A5BFB115651E1D97CD4262")
    # Get dicionary of events
    data = yes.json()
    yesbooking = data['data']

    # Values for json event for Fullcalendar
    for booking in yesbooking:

        if booking['group'] == None:
            name = "no event title"
        else:
            name = booking['group']['name']
        location = booking['locations'][0]['name']
        evstart = booking['starttime']
        evend = booking['endtime']

        # Make json event
        yesevent = {
          'title': f"{name} ({location})",
          'start': evstart,
          'end': evend,
          'url': "https://horsecross.yesplan.be/Yesplan",
          'color': "thistle"
          }
        # Add to events list
        events.append(yesevent)

    #----- Gannochy YesPlan Events ---->
    #Get json from Yesplan API
    yes = requests.get("https://horsecross.yesplan.be/api/events/location%3Agannochy%20date%3A%23next8months?api_key=5C76336690A5BFB115651E1D97CD4262")
    # Get dicionary of events
    data = yes.json()
    yesbooking = data['data']

    # Values for json event for Fullcalendar
    for booking in yesbooking:

        if booking['group'] == None:
            name = "no event title"
        else:
            name = booking['group']['name']
        location = booking['locations'][0]['name']
        evstart = booking['starttime']
        evend = booking['endtime']

        # Make json event
        yesevent = {
          'title': f"{name} ({location})",
          'start': evstart,
          'end': evend,
          'url': "https://horsecross.yesplan.be/Yesplan",
          'color': "lightblue"
          }
        # Add to events list
        events.append(yesevent)


    return render_template("calendar.php", events = events)

###----- Delete Booking ----->
@app.route("/delete/<id>", methods=["POST"])
@login_required
def delete(id):

    id=id
    #-----Delete booking from bookings table----->
    db.execute("DELETE FROM bookings WHERE id = :id", {"id": id})
    db.commit()

    return redirect("/booking")


""" Department Asset Lists """

###----- Department Asset Count ----->
@app.route("/dept/<dept>", methods=["GET", "POST"])
@login_required
def dept(dept):

    # Initiallize dictionary to contain type, quantity, and items
    itemcount = {}
    # Department returned from url argument (/dept/lighting... or Sound)
    dept = dept

    # Get types and items from selected department
    kit = db.execute("SELECT type, item FROM kit WHERE dept = :dept ORDER BY type ASC", {"dept": dept}).fetchall()

    # Iterate over types and items
    for row in kit:
        # Get item
        kititem = row['item']
        # Get count of item
        c = db.execute("SELECT COUNT( * ) FROM kit WHERE item = :item", {"item": kititem}).fetchall()
        count = c[0][0]
        # Get type
        t = db.execute("SELECT type FROM kit WHERE item = :item", {"item": kititem}).fetchone()
        type = t['type']

        #----- Create item count dictionary ----->
        if type in itemcount:
            if [type, count, kititem] not in itemcount[type]:
                # Append the new type to the existing array at this slot
                itemcount[type].append([type, count, kititem])
        else:
            # Create a new array in this slot
            itemcount[type] = [[type, count, kititem]]

    return render_template("dept.html", itemcount=itemcount, dept=dept)


""" QR Codes """

###----- QR codes ----->
@app.route("/qr", methods=["GET", "POST"])
@login_required
def qr():

    if request.method == "POST":
        #----- QR Query ----->
        if request.form.get("searchqr"):
            search = request.form.get("searchqr")
            # Add wildcard for database call
            search = f"%{search}%"

            # Search equipment for query
            kit = db.execute("SELECT * FROM kit WHERE dept ILIKE :search OR type ILIKE :search OR item ILIKE :search OR venue ILIKE :search", {"search": search}).fetchall()

            # Redirect user to QR page
            if not kit:
                flash('No items found')
                return redirect("/qr")
            else:
                return render_template("qr.html", kit = kit)

    # Get asset list by latest added
    kit = db.execute("SELECT * FROM kit ORDER BY id DESC").fetchall()

    return render_template("qr.html", kit = kit)


""" Login/Logout """

###----- Login ---->
@app.route("/login", methods=["GET", "POST"])
def login():

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":


        # Ensure username was submitted
        if not request.form.get("username"):
            flash("must provide username")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("must provide password")
            return render_template("login.html")

        name = request.form.get("username")
        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", {"username": name}).fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("invalid username and/or password")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

###----- Register ----->
@app.route("/register", methods=["GET", "POST"])
def register():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("must provide username")
            return render_template("register.html")

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                  {"username": request.form.get("username")}).fetchall()

        if len(rows) != 0:
            flash("The username is already taken")
            return render_template("register.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("must provide password")
            return render_template("register.html")

        # Ensure password confirmation was submitted
        elif not request.form.get("confirmation"):
            flash("must provide password confirmation")
            return render_template("register.html")

        # Ensure passwords are matching
        elif request.form.get("password") != request.form.get("confirmation"):
            flash("Passwords didn't match")
            return render_template("register.html")

        # Hash password / Store password hash_password =
        hashed_password = generate_password_hash(request.form.get("password"))

        # Add user to database
        result = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)",
                {"username": request.form.get("username"),
                "hash": hashed_password})
        db.commit()

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                  {"username": request.form.get("username")}).fetchall()

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

###----- Logout ----->
@app.route("/logout")
def logout():

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


""" Errors """

###----- Errors ----->
def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    flash(f"Error {e.code}, {e.name}")
    return redirect("/")


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
