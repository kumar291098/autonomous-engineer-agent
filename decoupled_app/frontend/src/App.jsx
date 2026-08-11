import React, { useState, useEffect } from 'react';
import './App.css';

export default function App() {
  const [orders, setOrders] = useState([
    { id: 1, customer: 'John Doe', amount: 29.99, status: 'DELIVERED' },
    { id: 2, customer: 'Jane Smith', amount: 45.50, status: 'PREPARING' }
  ]);

  return (
    <div className="dashboard-container">
      <header className="header">
        <h1>🚀 Food Order Dashboard</h1>
      </header>
      <main className="content">
        <div className="order-grid">
          {orders.map((o) => (
            <div key={o.id} className="order-card">
              <h3>Order #{o.id}</h3>
              <p>Customer: {o.customer}</p>
              <p>Amount: ${o.amount}</p>
              <span className={`badge ${o.status.toLowerCase()}`}>{o.status}</span>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
