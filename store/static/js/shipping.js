
document.addEventListener('DOMContentLoaded', function() {
    const stateSelect = document.getElementById('id_state'); // This is a <select> now
    const shippingDisplay = document.getElementById('shipping-cost-display');
    const totalDisplay = document.getElementById('total-cost-display');
    
    // We use |safe and |default:0 to ensure Django outputs a valid JS number
    const subtotal = parseFloat("{{ total_price|default:0 }}");

    // Change event is better for <select> than input
    stateSelect.addEventListener('change', function() {
        const state = this.value; // No need for .trim() on <select>
        let shippingFee = 0;

        if (state === "") {
            shippingFee = 0;
        } else if (["Sabah", "Sarawak"].includes(state)) {
            shippingFee = 15.00;
        } else {
            shippingFee = 5.00;
        }

        // Update UI
        shippingDisplay.innerText = "RM " + shippingFee.toFixed(2);
        const finalTotal = subtotal + shippingFee;
        totalDisplay.innerText = "RM " + finalTotal.toFixed(2);
    });
});