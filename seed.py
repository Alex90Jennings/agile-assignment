"""
Seed script — drops all tables and repopulates with demo data.

Speed note: password hashing is intentionally slow (bcrypt-like cost factor)
to protect real user accounts. For seeding, we compute ONE hash and reuse it
for every demo user. The application's set_password() method is unchanged and
remains secure for real registration and profile-edit flows.

Usage:
    python seed.py

Demo credentials:
    Admin    →  admin@example.com    /  Demo@1234   (confirmed)
    User     →  user@example.com     /  Demo@1234   (confirmed, has pending eSIM + top-up requests)
    Pending  →  pending@example.com  /  Demo@1234   (unconfirmed — awaiting approval)
"""

import sys
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import Business, User, ESim, Subscription

# ---------------------------------------------------------------------------
# Pre-compute one hash and reuse it for all seed users.
# This turns O(n) expensive hash operations into O(1).
# Password meets the app policy: 8+ chars, letter, number, special character.
# ---------------------------------------------------------------------------
SEED_PASSWORD = 'Demo@1234'

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

BUSINESSES = [
    ('Apex Telecom Ltd',        'REG-001'),
    ('BlueSky Networks',        'REG-002'),
    ('Cascade Connectivity',    'REG-003'),
    ('Delta Mobile Solutions',  'REG-004'),
    ('Echo Wireless',           'REG-005'),
    ('Frontier Digital',        'REG-006'),
    ('GlobalLink Systems',      'REG-007'),
    ('Horizon Broadband',       'REG-008'),
    ('Influx Communications',   'REG-009'),
    ('Jetstream Telecom',       'REG-010'),
]

# (first, last, email, is_admin, business_index, is_confirmed)
USERS = [
    ('Admin',   'User',    'admin@example.com',   True,  0, True),   # admin — always confirmed
    ('Demo',    'User',    'user@example.com',    False, 0, True),    # confirmed regular user
    ('Pending', 'Account', 'pending@example.com', False, 0, False),  # unconfirmed — for demo
    ('Alice',   'Johnson', 'alice@apex.com',      False, 0, True),
    ('Bob',     'Smith',   'bob@bluesky.com',     False, 1, True),
    ('Carol',   'White',   'carol@cascade.com',   False, 2, True),
    ('David',   'Brown',   'david@delta.com',     False, 3, True),
    ('Eve',     'Davis',   'eve@echo.com',        False, 4, True),
    ('Frank',   'Miller',  'frank@frontier.com',  False, 5, True),
    ('Grace',   'Wilson',  'grace@global.com',    False, 6, True),
    ('Henry',   'Moore',   'henry@horizon.com',   False, 7, True),
    ('Isla',    'Taylor',  'isla@influx.com',     False, 8, True),
    ('Jack',    'Anderson','jack@jetstream.com',  False, 9, True),
]

# ICCIDs are 19-22 digit SIM identifiers
# (iccid, label, status, user_index)
ESIMS = [
    ('8944501234567890001', 'Work Phone',    'active',    1),
    ('8944501234567890002', 'Travel eSIM',   'active',    3),
    ('8944501234567890003', 'Primary',       'active',    4),
    ('8944501234567890004', 'Backup',        'inactive',  5),
    ('8944501234567890005', 'Office Device', 'active',    6),
    ('8944501234567890006', 'Field Tablet',  'suspended', 7),
    ('8944501234567890007', 'Home Router',   'active',    8),
    ('8944501234567890008', 'Personal',      'active',    9),
    ('8944501234567890009', 'Test SIM',      'inactive', 10),
    ('8944501234567890010', 'Dev Device',    'active',   11),
]

PLANS = [
    ('Starter 5GB',   5.0),
    ('Standard 20GB', 20.0),
    ('Pro 50GB',      50.0),
    ('Unlimited',     999.0),
    ('Travel 10GB',   10.0),
]


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

def seed():
    app = create_app('development')

    with app.app_context():
        print('Dropping all tables...')
        db.drop_all()

        print('Creating all tables...')
        db.create_all()

        # Hash once, reuse for every demo user
        print(f'Hashing seed password (once)...')
        seed_hash = generate_password_hash(SEED_PASSWORD)

        # Businesses
        print(f'Inserting {len(BUSINESSES)} businesses...')
        businesses = []
        for name, reg in BUSINESSES:
            b = Business(name=name, registration_number=reg)
            db.session.add(b)
            businesses.append(b)
        db.session.flush()

        # Users — assign the pre-computed hash directly
        print(f'Inserting {len(USERS)} users...')
        users = []
        for first, last, email, is_admin, biz_idx, is_confirmed in USERS:
            u = User(
                first_name=first,
                last_name=last,
                email=email,
                password_hash=seed_hash,   # reuse pre-computed hash
                is_admin=is_admin,
                is_confirmed=is_confirmed,
                business_id=businesses[biz_idx].id,
            )
            db.session.add(u)
            users.append(u)
        db.session.flush()

        # eSIMs
        print(f'Inserting {len(ESIMS)} eSIMs...')
        esims = []
        for iccid, label, status, user_idx in ESIMS:
            e = ESim(
                iccid=iccid,
                label=label,
                status=status,
                is_confirmed=True,
                user_id=users[user_idx].id,
            )
            db.session.add(e)
            esims.append(e)
        db.session.flush()

        # Subscriptions — one per eSIM cycling through plans, plus a second
        # wave for the first five eSIMs so they have multiple subscriptions
        today = date.today()
        sub_count = 0

        for i, esim in enumerate(esims):
            plan_name, data_gb = PLANS[i % len(PLANS)]
            start = today - timedelta(days=30 * (i + 1))
            end = start + timedelta(days=30)
            sub_status = 'expired' if end < today else 'active'
            db.session.add(Subscription(
                esim_id=esim.id,
                plan_name=plan_name,
                data_limit_gb=data_gb,
                start_date=start,
                end_date=end,
                status=sub_status,
                is_confirmed=True,
            ))
            sub_count += 1

        for i, esim in enumerate(esims[:5]):
            plan_name, data_gb = PLANS[(i + 2) % len(PLANS)]
            db.session.add(Subscription(
                esim_id=esim.id,
                plan_name=plan_name,
                data_limit_gb=data_gb,
                start_date=today - timedelta(days=10),
                end_date=None,
                status='active',
                is_confirmed=True,
            ))
            sub_count += 1

        # Pending eSIM request from demo user — awaiting admin approval
        pending_esim = ESim(
            iccid='8999999999999999001',
            label='New Device',
            status='inactive',
            is_confirmed=False,
            user_id=users[1].id,   # user@example.com
        )
        db.session.add(pending_esim)
        db.session.flush()

        db.session.add(Subscription(
            esim_id=pending_esim.id,
            plan_name='Starter 5GB',
            data_limit_gb=5.0,
            start_date=today,
            end_date=None,
            status='active',
            is_confirmed=False,
        ))
        sub_count += 1

        # Pending top-up request on demo user's existing eSIM
        db.session.add(Subscription(
            esim_id=esims[0].id,   # Work Phone
            plan_name='Extra 10GB Boost',
            data_limit_gb=10.0,
            start_date=today,
            end_date=None,
            status='active',
            is_confirmed=False,
        ))
        sub_count += 1

        # Additional pending top-up requests on confirmed eSIMs — enough to
        # push the pending subscription table past per_page=5 and show pagination
        pending_topups = [
            (esims[1].id, 'Pro 50GB',        50.0),   # Travel eSIM — alice@apex.com
            (esims[2].id, 'Standard 20GB',   20.0),   # Primary      — bob@bluesky.com
            (esims[3].id, 'Travel 10GB',     10.0),   # Backup        — carol@cascade.com
            (esims[4].id, 'Unlimited',       999.0),  # Office Device — david@delta.com
            (esims[5].id, 'Starter 5GB',     5.0),    # Field Tablet  — eve@echo.com
        ]
        for esim_id, plan_name, data_gb in pending_topups:
            db.session.add(Subscription(
                esim_id=esim_id,
                plan_name=plan_name,
                data_limit_gb=data_gb,
                start_date=today,
                end_date=None,
                status='active',
                is_confirmed=False,
            ))
            sub_count += 1

        pending_sub_count = 2 + len(pending_topups)   # original 2 + new 5
        print(f'Inserting {sub_count} subscriptions ({pending_sub_count} pending)...')
        db.session.commit()

        print()
        print('=' * 56)
        print('  Database seeded successfully.')
        print('=' * 56)
        print(f'  Businesses : {len(businesses)}')
        print(f'  Users      : {len(users)}')
        print(f'  eSIMs      : {len(esims)}')
        print(f'  Subscriptions: {sub_count} ({pending_sub_count} pending)')
        print()
        print('  Demo credentials (all accounts use the same password):')
        print(f'  Admin    →  admin@example.com    /  {SEED_PASSWORD}  (confirmed)')
        print(f'  User     →  user@example.com     /  {SEED_PASSWORD}  (confirmed)')
        print(f'  Pending  →  pending@example.com  /  {SEED_PASSWORD}  (unconfirmed)')
        print('=' * 56)


if __name__ == '__main__':
    seed()
