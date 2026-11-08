const speakeasy = require('speakeasy');

const generateSecret = () => speakeasy.generateSecret({
  name: 'SmartFin AI',
});

const verifyToken = (token, secret) => speakeasy.totp.verify({
  token,
  secret,
  encoding: 'base32',
});

module.exports = { generateSecret, verifyToken };
