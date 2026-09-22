document.addEventListener('click', function (e) {
    // 1. Detect clicks on Add to Cart, Quantity adjustments, or Remove buttons
    const target = e.target.closest('.ajax-add-to-cart, .ajax-update');
    
    if (target) {
        e.preventDefault();
        const url = target.getAttribute('href');
        
        // Select all potential UI elements that need updating
        const cartBadge = document.getElementById('cart-badge');
        const dropdownContainer = document.querySelector('.cart-dropdown .dropdown-menu');
        const checkoutSummary = document.getElementById('checkout-items-container');

        fetch(url, {
            method: 'GET',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                
                // 2. Update the Navbar Badge count
                if (cartBadge) {
                    cartBadge.innerText = data.total_items;
                    // Toggle visibility: hide if 0, show if > 0
                    if (data.total_items > 0) {
                        cartBadge.classList.remove('d-none');
                    } else {
                        cartBadge.classList.add('d-none');
                    }
                }

                // 3. Update the Dropdown Menu (Header)
                if (dropdownContainer && data.cart_html) {
                    dropdownContainer.innerHTML = data.cart_html;
                }

                // 4. Update the Checkout Page Summary (Main Body)
                // This checks if the user is currently on the checkout page
                if (checkoutSummary && data.cart_html) {
                    checkoutSummary.innerHTML = data.cart_html;
                }

                // 5. If the cart becomes empty while on Checkout, redirect to home
                if (data.total_items === 0 && window.location.pathname.includes('checkout')) {
                    window.location.href = '/'; 
                }
            }
        })
        .catch(error => console.error('Error fetching cart update:', error));
    }
});