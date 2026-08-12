import React from 'react';
import { createRoot } from 'react-dom/client';
import { PopupApp } from './PopupApp';
import './popup.css';

const container = document.getElementById('root');
if (!container) throw new Error('popup root missing');
createRoot(container).render(
  <React.StrictMode>
    <PopupApp />
  </React.StrictMode>,
);
