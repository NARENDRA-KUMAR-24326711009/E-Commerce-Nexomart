// ─── ADD TO CART ───────────────────────────────────────────────────────────────
function addToCart(pid, btn) {
    const form = new FormData();
    form.append('quantity', 1);
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Adding...';
    }
    fetch(`/cart/add/${pid}`, { method: 'POST', body: form })
        .then(r => r.json())
        .then(d => {
            if (d.success) {
                updateCartBadge(d.cart_count);
                showToast('✓ Added to cart!');
                if (btn) {
                    btn.innerHTML = '<i class="fa fa-check"></i> Added!';
                    btn.style.background = '#388e3c';
                    setTimeout(() => {
                        btn.innerHTML = '<i class="fa fa-cart-plus"></i> Add to Cart';
                        btn.style.background = '';
                        btn.disabled = false;
                    }, 1500);
                }
            } else {
                window.location.href = '/login';
            }
        })
        .catch(() => {
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa fa-cart-plus"></i> Add to Cart'; }
        });
}

// ─── CART BADGE ────────────────────────────────────────────────────────────────
function updateCartBadge(count) {
    let badge = document.getElementById('cartBadge');
    if (!badge) {
        const cartLink = document.querySelector('.cart-link');
        if (cartLink) {
            badge = document.createElement('span');
            badge.id = 'cartBadge';
            badge.className = 'cart-badge';
            cartLink.appendChild(badge);
        }
    }
    if (badge) badge.textContent = count;
}

// ─── TOAST ─────────────────────────────────────────────────────────────────────
function showToast(msg) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity .3s'; }, 2500);
    setTimeout(() => toast.remove(), 2800);
}

// ─── SEARCH SUGGESTIONS ────────────────────────────────────────────────────────
const searchInput = document.getElementById('searchInput');
const suggestionsBox = document.getElementById('searchSuggestions');

if (searchInput && suggestionsBox) {
    let timeout;
    searchInput.addEventListener('input', function () {
        clearTimeout(timeout);
        const q = this.value.trim();
        if (q.length < 2) { suggestionsBox.innerHTML = ''; return; }
        timeout = setTimeout(() => {
            fetch(`/api/search_suggestions?q=${encodeURIComponent(q)}`)
                .then(r => r.json())
                .then(items => {
                    if (!items.length) { suggestionsBox.innerHTML = ''; return; }
                    suggestionsBox.innerHTML = items.map(item =>
                        `<div class="suggestion-item" onclick="window.location='/product/${item.id}'">
                            <span>${item.name}</span>
                            <span>₹${item.price.toLocaleString('en-IN')}</span>
                        </div>`
                    ).join('');
                });
        }, 300);
    });

    document.addEventListener('click', e => {
        if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
            suggestionsBox.innerHTML = '';
        }
    });
}

// ─── AUTO DISMISS FLASH ────────────────────────────────────────────────────────
document.querySelectorAll('.flash').forEach(flash => {
    setTimeout(() => {
        flash.style.transition = 'opacity .4s';
        flash.style.opacity = '0';
        setTimeout(() => flash.remove(), 400);
    }, 4000);
});
