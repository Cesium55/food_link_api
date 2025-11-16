(function() {
    const paymentId = window.PAYMENT_ID;
    const paymentStatus = window.PAYMENT_STATUS;
    const purchaseId = window.PURCHASE_ID;
    
    if (window.ReactNativeWebView) {
        window.ReactNativeWebView.postMessage(JSON.stringify({
            type: 'payment_status',
            status: paymentStatus,
            payment_id: paymentId,
            purchase_id: purchaseId
        }));
    } else {
        console.log('Payment status:', paymentStatus, 'Payment ID:', paymentId);
    }
})();

