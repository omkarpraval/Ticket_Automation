"""8 handwritten starter KB articles, one per common seeded category. These exist so
retrieval has real grounded answers from the very first run, before any incident has
ever been resolved into a synthesized article.
"""

KB_SEED_ARTICLES = [
    {
        "title": "VPN client fails to connect or drops repeatedly",
        "tags": ["vpn", "network", "remote-access"],
        "symptom": (
            "User cannot establish a VPN connection, the client hangs at 'Connecting...', or an "
            "established VPN session drops every few minutes, especially on home Wi-Fi."
        ),
        "cause": (
            "The most common cause is a stale or expired VPN client configuration profile after a "
            "gateway certificate rotation. A secondary cause is the client competing with a second "
            "network adapter (e.g. a second Wi-Fi/Ethernet interface) that changes the default route "
            "mid-session, which the client interprets as a network change and drops the tunnel."
        ),
        "resolution_steps": (
            "1. Confirm the user is on a supported network (public hotel/airport Wi-Fi with "
            "captive portals often blocks the VPN's UDP port).\n"
            "2. Have the user fully quit the VPN client (not just disconnect) and relaunch it.\n"
            "3. Delete the client's cached profile and re-download it from the self-service portal - "
            "this forces re-sync of the current gateway certificate.\n"
            "4. If the machine has more than one active network adapter, disable the unused one for "
            "the duration of the VPN session.\n"
            "5. Check the gateway logs for repeated re-key failures for this user's certificate; if "
            "present, revoke and reissue the client certificate."
        ),
        "verification": (
            "Ask the user to stay connected and idle for 10 minutes, then run a sustained file "
            "transfer or video call for 5 minutes without a drop."
        ),
    },
    {
        "title": "MFA prompts fail or SSO login loops back to the login page",
        "tags": ["sso", "mfa", "identity", "authentication"],
        "symptom": (
            "User enters their password successfully but the MFA push notification never arrives, "
            "or after approving MFA they are bounced back to the SSO login screen in a loop."
        ),
        "cause": (
            "A login loop after successful MFA is almost always a clock-skew or stale-session-cookie "
            "issue between the identity provider and the target application. Missing push "
            "notifications are usually a device re-registration problem after a phone replacement "
            "or OS reinstall that orphaned the old MFA device binding."
        ),
        "resolution_steps": (
            "1. Ask if the user recently got a new phone or reinstalled the authenticator app.\n"
            "2. If so, remove the old MFA device binding in the identity admin console and send the "
            "user a fresh enrollment link.\n"
            "3. For login loops, have the user clear cookies for the SSO domain and the target app "
            "domain, then retry in a private/incognito window to rule out a stale session cookie.\n"
            "4. Confirm the user's device clock is set to automatic (network time) - MFA codes are "
            "time-based and drift causes silent rejection.\n"
            "5. If the loop persists across a clean browser profile, check the app's SSO integration "
            "logs for a SAML assertion signature mismatch and escalate to identity engineering."
        ),
        "verification": "User completes a fresh login end-to-end from a signed-out state without a loop or missing prompt.",
    },
    {
        "title": "Account locked out after repeated failed password attempts",
        "tags": ["password", "lockout", "identity"],
        "symptom": "User is told their account is locked and cannot sign in, even with the correct password.",
        "cause": (
            "Lockouts are almost always caused by a stale saved credential in a second location - a "
            "mobile mail app, a mapped network drive, or a browser's saved password - retrying "
            "automatically in the background with the old password after a recent password change."
        ),
        "resolution_steps": (
            "1. Unlock the account in the identity admin console.\n"
            "2. Ask when the user last changed their password, and whether they use a phone mail app "
            "or have any mapped drives.\n"
            "3. Have the user update the saved credential on their phone's mail app and any mapped "
            "network drives to the new password.\n"
            "4. Clear saved passwords for the company domain in the browser's password manager.\n"
            "5. If lockouts continue with no obvious second location, check the sign-in log for the "
            "source IP/device of the failed attempts - it may indicate a compromised credential rather "
            "than a stale client, in which case force a password reset and escalate to security."
        ),
        "verification": "User successfully signs in once, and no further lockout occurs over the next hour.",
    },
    {
        "title": "Mailbox over quota - cannot send or receive mail",
        "tags": ["email", "mailbox", "quota", "collaboration"],
        "symptom": "User gets a bounce-back or 'mailbox full' error when sending, or stops receiving new mail entirely.",
        "cause": (
            "Mailbox quota is exceeded, most commonly from large attachments left in Sent Items or an "
            "auto-archive/retention policy that stopped running after a client update."
        ),
        "resolution_steps": (
            "1. Check current mailbox size against quota in the admin console.\n"
            "2. Sort the mailbox by size and identify the largest folders (Sent Items and Deleted "
            "Items are the usual offenders).\n"
            "3. Have the user move large attachments to the shared drive and delete them from mail, "
            "or archive to a local/online archive if policy allows.\n"
            "4. Empty Deleted Items and Junk after moving items out.\n"
            "5. If the user is a legitimate heavy mail user, submit a quota increase request instead "
            "of repeated manual cleanup."
        ),
        "verification": "Mailbox size drops below quota and a test email round-trips successfully.",
    },
    {
        "title": "Printer not visible or jobs stuck in queue",
        "tags": ["printer", "peripherals", "hardware"],
        "symptom": "A shared printer no longer appears in the print dialog, or jobs sit in 'Printing...' and never complete.",
        "cause": (
            "Most commonly the print spooler service is hung, or the printer's DHCP lease renewed "
            "with a new IP address that the print server's port configuration still points at the "
            "old address for."
        ),
        "resolution_steps": (
            "1. On the user's machine, clear the stuck job and restart the Print Spooler service.\n"
            "2. Ping the printer's hostname to confirm it resolves to the address on the printer's own "
            "network settings page.\n"
            "3. If the IP has changed, update the printer port on the print server to the new address, "
            "or reserve a static/DHCP-reservation IP for the printer to prevent recurrence.\n"
            "4. Reinstall the printer on the affected workstation using the print server's shared "
            "queue rather than a direct IP connection where possible.\n"
            "5. If multiple users on the same floor are affected, treat this as a shared-printer "
            "outage rather than a single-user issue."
        ),
        "verification": "A test page prints successfully from the previously affected workstation.",
    },
    {
        "title": "VDI / virtual desktop session is slow, freezes, or fails to launch",
        "tags": ["vdi", "virtual-desktop", "performance"],
        "symptom": "Virtual desktop session takes minutes to load, freezes intermittently, or the launch fails with a connection error.",
        "cause": (
            "Launch failures are usually a stale session left checked out on another host after an "
            "ungraceful disconnect. Slowness/freezing during a session is usually host-side resource "
            "contention (CPU/memory oversubscription) on the hypervisor pool the user was assigned to."
        ),
        "resolution_steps": (
            "1. For launch failures, check the VDI broker for an orphaned session under the user's "
            "account and force-reset it.\n"
            "2. Have the user retry the launch after the reset.\n"
            "3. For slowness, check host-level CPU ready time and memory ballooning on the hypervisor "
            "hosting the user's pool.\n"
            "4. If the pool is oversubscribed, migrate the user's desktop to a less-loaded host or "
            "flag the pool for capacity review.\n"
            "5. Confirm the user's local network path to the VDI gateway isn't the bottleneck by "
            "checking round-trip latency from their location."
        ),
        "verification": "Session launches within the normal SLA window and remains responsive for 15 minutes of active use.",
    },
    {
        "title": "Cannot access shared network drive or folder - access denied",
        "tags": ["shared-drive", "file-access", "permissions"],
        "symptom": "User gets 'Access is denied' or the drive fails to map when opening a shared folder they previously had access to.",
        "cause": (
            "Usually a group membership change did not propagate (Kerberos ticket cache still holds "
            "the old group list), or the user was moved between departments and their old group's "
            "share permissions were revoked without the new group being granted equivalent access."
        ),
        "resolution_steps": (
            "1. Confirm in the identity admin console which security group actually grants access to "
            "the share in question.\n"
            "2. Check whether the user is currently a member of that group.\n"
            "3. If they were just added, have them sign out and back in (or run a Kerberos ticket "
            "refresh) so the new group membership takes effect - propagation is not always instant.\n"
            "4. If they are not a member, add them to the correct group rather than granting a direct "
            "ACL on the folder, to keep access reviewable.\n"
            "5. Re-map the drive from a fresh session and confirm read/write as expected for their role."
        ),
        "verification": "User can open, and where expected write to, the shared folder from a freshly signed-in session.",
    },
    {
        "title": "Laptop is very slow to boot or unresponsive during normal use",
        "tags": ["laptop", "endpoint", "performance"],
        "symptom": "Laptop takes several minutes to boot, or becomes sluggish/unresponsive during normal office use (browser, mail, video calls).",
        "cause": (
            "Most often disk space below 10% free (blocking OS/app swap and update staging) combined "
            "with a heavy set of startup applications, or a background full-disk antivirus scan "
            "colliding with business hours."
        ),
        "resolution_steps": (
            "1. Check free disk space; if below 10%, clean temp files and have the user move large "
            "local files to the shared drive or OneDrive.\n"
            "2. Review startup applications and disable non-essential ones.\n"
            "3. Check whether a full antivirus/disk scan is scheduled during work hours and reschedule "
            "it to off-hours.\n"
            "4. Confirm available RAM against the number of concurrent apps/browser tabs typically "
            "open - recommend closing unused tabs as a stopgap.\n"
            "5. If the machine is older hardware near end-of-life and the above doesn't resolve it, "
            "flag for a hardware refresh rather than repeated remediation."
        ),
        "verification": "Boot time returns to under a minute and the user reports normal responsiveness over a full day.",
    },
]
