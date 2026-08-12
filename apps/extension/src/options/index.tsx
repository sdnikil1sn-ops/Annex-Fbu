import React from 'react';
import { createRoot } from 'react-dom/client';
import { OptionsApp } from './OptionsApp';
import './options.css';

const container = document.getElementById('root');
if (!container) throw new Error('options root missing');
createRoot(container).render(
  <React.StrictMode>
    <OptionsApp />
  </React.StrictMode>,
);
