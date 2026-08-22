"""Admin authentication and admin-only action routes."""
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from admin_auth import admin_required, check_credentials, is_admin

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if is_admin():
        return redirect(url_for("admin.admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username") or ""
        password = request.form.get("password") or ""
        if check_credentials(username, password):
            session.clear()
            session["is_admin"] = True
            session.permanent = True
            flash("Logged in as admin.", "info")
            return redirect(url_for("admin.admin_dashboard"))
        flash("Invalid username or password.", "error")

    return render_template("admin_login.html")


@admin_bp.route("/admin/dashboard")
def admin_dashboard():
    if not is_admin():
        return redirect(url_for("admin.admin_login"))
    return render_template("admin_dashboard.html")


@admin_bp.route("/admin/logout", methods=["GET", "POST"])
def admin_logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("main.index"))


@admin_bp.route("/admin/ping")
@admin_required
def admin_ping():
    """Example admin-only endpoint — pattern for future mutating routes."""
    return jsonify(ok=True, admin=True)


@admin_bp.route("/admin/clear-message", methods=["POST"])
@admin_required
def admin_clear_message():
    """Authorize clearing the message field (UI clears only after this succeeds)."""
    return jsonify(ok=True)
