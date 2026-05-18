const axios = require('axios');

const api = axios.create();

api.interceptors.request.use(config => {
  console.log("Type of config.data:", typeof config.data);
  try {
    JSON.parse(config.data);
  } catch (e) {
    console.error("Parse error:", e.message);
  }
  return config;
});

api.post('/test', { hello: 'world' }).catch(() => {});
