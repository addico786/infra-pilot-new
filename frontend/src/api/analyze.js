// frontend/src/api/analyze.js
import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const analyzeFile = async ({ content, fileName, emailRecipients, model }) => {
  const response = await axios.post(`${BASE_URL}/analyze`, {
    content,
    file_name: fileName,
    email_recipients: emailRecipients,
    model: model || null,
  });
  return response.data;
};

export const getHealth = async () => {
  const response = await axios.get(`${BASE_URL}/health`);
  return response.data;
};
