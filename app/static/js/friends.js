$(function () {
    let friendReqCount = 0;
    let chalReqCount = 0;

    function getCSRFToken() {
        return $('meta[name="csrf-token"]').attr('content');
    }

    // ── Load friends list ─────────────────────────────────────────────
    function loadFriends() {
        $.when(
            $.ajax({ url: '/api/friends', method: 'GET' }),
            $.ajax({ url: '/api/challenges/active', method: 'GET' })
        ).then(function (friendsRes, challengesRes) {
            const friends = friendsRes[0];
            const challenges = challengesRes[0];
            
            chalReqCount = challenges.filter(c => c.challenged_id == window.current_user_id && c.status === 'pending').length;
            updateBadges();
            
            const section = $('#friends-list-section');
            section.find('.friend-card').remove();
            section.find('.friends-empty-message').remove();

            if (friends.length === 0) {
                section.append('<p class="friends-empty-message text-muted-light small mt-2">No friends yet. Search for players to add!</p>');
                return;
            }

            friends.forEach(function (f) {
                const initials = f.username.substring(0, 2).toUpperCase();
                
                // Find if there is an active challenge with this friend
                const activeChallenge = challenges.find(c => 
                    (c.challenger_id === f.uid || c.challenged_id === f.uid) &&
                    (c.status === 'pending' || c.status === 'ready_waiting' || c.status === 'in_progress')
                );

                let buttonHtml = '';
                if (!activeChallenge) {
                    buttonHtml = `
                        <button class="btn btn-warning btn-sm challenge-invite-btn bangers-font mt-1" data-uid="${f.uid}">
                            Challenge
                        </button>
                    `;
                } else {
                    const isChallenger = activeChallenge.challenger_id === current_user_id;
                    const status = activeChallenge.status;
                    
                    if (status === 'pending') {
                        if (isChallenger) {
                            buttonHtml = `
                                <button class="btn btn-outline-warning btn-sm challenge-play-btn bangers-font mt-1" data-id="${activeChallenge.id}">
                                    Challenge Sent
                                </button>
                            `;
                        } else {
                            buttonHtml = `
                                <div class="d-flex gap-1 mt-1">
                                    <button class="btn btn-warning btn-sm challenge-accept-btn bangers-font" data-id="${activeChallenge.id}">Accept</button>
                                    <button class="btn btn-outline-light btn-sm challenge-reject-btn bangers-font" data-id="${activeChallenge.id}">Decline</button>
                                </div>
                            `;
                        }
                    } else if (status === 'ready_waiting' || status === 'in_progress') {
                        const userFinished = isChallenger ? (activeChallenge.challenger_round >= 6) : (activeChallenge.challenged_round >= 6);
                        if (userFinished) {
                            buttonHtml = `
                                <button class="btn btn-warning btn-sm challenge-play-btn bangers-font mt-1" data-id="${activeChallenge.id}">
                                    See Game
                                </button>
                            `;
                        } else {
                            buttonHtml = `
                                <button class="btn btn-warning btn-sm challenge-play-btn bangers-font mt-1" data-id="${activeChallenge.id}">
                                    Enter Game
                                </button>
                            `;
                        }
                    }
                }

                // Avatar and name wrapped in link to user's profile
                section.append(`
                    <div class="friend-card">
                        <a href="/user/${f.username}" class="friend-card__avatar-link" style="text-decoration:none;">
                            <div class="friend-card__avatar">${initials}</div>
                        </a>
                        <div class="friend-card__meta">
                            <a href="/user/${f.username}" class="friend-card__name" style="color:var(--text-light);text-decoration:none;">
                                ${f.username}
                            </a>
                            <div class="friend-card__label">${f.total_score ? f.total_score.toLocaleString() + ' pts' : 'No score yet'}</div>
                            ${buttonHtml}
                        </div>
                    </div>
                `);
            });
        });
    }

    // ── Load pending requests ─────────────────────────────────────────
    function loadPendingRequests() {
        $.ajax({
            url: '/api/friends/requests',
            method: 'GET',
            success: function (requests) {
                const section = $('#pending-invites-section');
                section.find('.pending-card').remove();
                
                if (requests.length === 0) {
                    section.hide();
                    friendReqCount = 0;
                    updateBadges();
                } else {
                    section.show();
                    requests.forEach(function (r) {
                        const initials = r.username.substring(0, 2).toUpperCase();
                        section.append(`
                            <div class="pending-card" data-id="${r.id}">
                                <a href="/user/${r.username}" style="text-decoration:none;">
                                    <div class="pending-card__avatar">${initials}</div>
                                </a>
                                <div class="pending-card__meta">
                                    <a href="/user/${r.username}" class="pending-card__title" style="color:var(--text-light);text-decoration:none;">${r.username}</a>
                                    <div class="d-flex gap-2 mt-1">
                                        <button class="btn btn-warning btn-sm bangers-font accept-btn" data-id="${r.id}">Accept</button>
                                        <button class="btn btn-outline-light btn-sm bangers-font reject-btn" data-id="${r.id}">Reject</button>
                                    </div>
                                </div>
                            </div>
                        `);
                    });
                    friendReqCount = requests.length;
                    updateBadges();
                }
            }
        });
    }
    
    function updateBadges() {
        const toggleBadge = $('#friends-toggle-badge');
        const total = friendReqCount + chalReqCount;

        if (total > 0) {
            toggleBadge.text(total > 9 ? '9+' : total).show();
        } else {
            toggleBadge.hide();
        }
    }

    // ── Search users ──────────────────────────────────────────────────
    let searchTimeout;
    $('#friends-search').on('input', function () {
        clearTimeout(searchTimeout);
        const query = $(this).val().trim();

        if (query.length < 2) {
            $('#search-results').remove();
            return;
        }

        searchTimeout = setTimeout(function () {
            $.ajax({
                url: '/api/friends/search?q=' + encodeURIComponent(query),
                method: 'GET',
                success: function (users) {
                    $('#search-results').remove();
                    if (users.length === 0) return;

                    let html = '<div id="search-results">';
                    users.forEach(function (u) {
                        let btnHtml = '';
                        if (u.friendship_status === 'friends') {
                            btnHtml = '<span class="text-muted small">Friends</span>';
                        } else if (u.friendship_status === 'sent') {
                            btnHtml = '<span class="badge" style="background:rgba(255,202,44,0.2);color:var(--golden);border:1px solid var(--golden);border-radius:0.5rem;padding:0.25rem 0.5rem;font-size:0.75rem;">⏳ Invite Sent</span>';
                        } else if (u.friendship_status === 'received') {
                            btnHtml = '<span class="text-muted small">Wants to add you</span>';
                        } else {
                            btnHtml = `<button class="btn btn-warning btn-sm bangers-font add-friend-btn" data-uid="${u.uid}">Add</button>`;
                        }

                        const initials = u.username.substring(0, 2).toUpperCase();
                        html += `
                            <div class="friend-card mt-2">
                                <a href="/user/${u.username}" style="text-decoration:none;">
                                    <div class="friend-card__avatar">${initials}</div>
                                </a>
                                <div class="friend-card__meta">
                                    <a href="/user/${u.username}" class="friend-card__name" style="color:var(--text-light);text-decoration:none;">${u.username}</a>
                                    <div>${btnHtml}</div>
                                </div>
                            </div>
                        `;
                    });
                    html += '</div>';
                    $('#friends-search').after(html);
                }
            });
        }, 400);
    });

    // ── Add friend button (from search results) ───────────────────────
    $(document).on('click', '.add-friend-btn', function () {
        const uid = $(this).data('uid');
        const $btn = $(this);
        $btn.prop('disabled', true).text('Sending...');

        $.ajax({
            url: '/api/friends/add',
            method: 'POST',
            contentType: 'application/json',
            headers: { 'X-CSRFToken': getCSRFToken() },
            data: JSON.stringify({ uid: uid }),
            success: function () {
                $btn.text('Requested').prop('disabled', true);
            },
            error: function (xhr) {
                $btn.prop('disabled', false).text('Add');
                alert(xhr.responseJSON?.error || 'Something went wrong');
            }
        });
    });

    // ── Accept/Reject friend requests ─────────────────────────────────
    $(document).on('click', '.accept-btn, .reject-btn', function () {
        const id = $(this).data('id');
        const action = $(this).hasClass('accept-btn') ? 'accept' : 'reject';
        const $card = $(this).closest('.pending-card');

        $.ajax({
            url: '/api/friends/respond',
            method: 'POST',
            contentType: 'application/json',
            headers: { 'X-CSRFToken': getCSRFToken() },
            data: JSON.stringify({ id: id, action: action }),
            success: function () {
                $card.remove();
                loadFriends();
                loadPendingRequests();
            }
        });
    });

    // ── Add Friend button (focuses search) ────────────────────────────
    $('#friends-add').on('click', function () {
        $('#friends-search').focus();
    });

    // ── Challenge Logic ──────────────────────────────────────────────
    $(document).on('click', '.challenge-invite-btn', function () {
        const uid = $(this).data('uid');
        const $btn = $(this);
        $btn.prop('disabled', true).text('Inviting...');

        $.ajax({
            url: '/api/challenges/create',
            method: 'POST',
            contentType: 'application/json',
            headers: { 'X-CSRFToken': getCSRFToken() },
            data: JSON.stringify({ uid: uid }),
            success: function (data) {
                if (data.redirect) {
                    window.location.href = data.redirect;
                    return;
                }
                loadFriends();
                loadPendingRequests();
            },
            error: function (xhr) {
                $btn.prop('disabled', false).text('Challenge');
                alert(xhr.responseJSON?.error || 'Something went wrong');
            }
        });
    });

    $(document).on('click', '.challenge-accept-btn', function () {
        const id = $(this).data('id');
        const $btn = $(this);
        $btn.prop('disabled', true);

        $.ajax({
            url: '/api/challenges/respond',
            method: 'POST',
            contentType: 'application/json',
            headers: { 'X-CSRFToken': getCSRFToken() },
            data: JSON.stringify({ id: id, action: 'accept' }),
            success: function (data) {
                window.location.href = `/game?challengeId=${id}`;
            },
            error: function (xhr) {
                $btn.prop('disabled', false);
                alert(xhr.responseJSON?.error || 'This challenge is no longer available');
                loadFriends();
                loadPendingRequests();
            }
        });
    });

    $(document).on('click', '.challenge-reject-btn', function () {
        const id = $(this).data('id');

        $.ajax({
            url: '/api/challenges/respond',
            method: 'POST',
            contentType: 'application/json',
            headers: { 'X-CSRFToken': getCSRFToken() },
            data: JSON.stringify({ id: id, action: 'reject' }),
            success: function () {
                loadFriends();
                loadPendingRequests();
            }
        });
    });

    $(document).on('click', '.challenge-play-btn', function () {
        const id = $(this).data('id');
        window.location.href = `/game?challengeId=${id}`;
    });

    // ── Refresh button ─────────────────────────────────────────────
    $('#friends-refresh').on('click', function () {
        loadFriends();
        loadPendingRequests();
    });

    // ── Initial load ───────────────────────
    loadFriends();
    loadPendingRequests();

    // ── Global WebSocket for challenges/notifications ────────────────
    let socket = null;
    if (window.current_user_id) {
        socket = io();
        socket.on('connect', () => {
            socket.emit('join_global', { user_id: window.current_user_id });
        });
        
        socket.on('new_challenge', (data) => {
            loadFriends();
            loadPendingRequests();
        });

        socket.on('friend_request_update', () => {
            loadFriends();
            loadPendingRequests();
        });

        socket.on('friend_list_update', () => {
            loadFriends();
            loadPendingRequests();
        });

        socket.on('ready_update', () => {
            loadFriends();
            loadPendingRequests();
        });

        socket.on('status_update', () => {
            loadFriends();
            loadPendingRequests();
        });
    }
});