const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const { generateSecret, verifyToken } = require('../services/2faService');

const JWT_SECRET = process.env.JWT_SECRET || 'smartfin-dev-secret';

const register = async (req, res) => {
  const { email, password } = req.body || {};

  if (!email || !password) {
    return res.status(422).json({ status: 'error', errors: ['Email and password are required'] });
  }

  try {
    const hashed = await bcrypt.hash(password, 10);
    const userId = 1;

    return res.status(201).json({
      status: 'ok',
      data: { userId, email },
    });
  } catch (err) {
    return res.status(500).json({ status: 'error', errors: ['Registration failed'] });
  }
};

const login = async (req, res) => {
  const { email, password, token } = req.body || {};

  if (!email || !password) {
    return res.status(422).json({ status: 'error', errors: ['Email and password are required'] });
  }

  try {
    if (token) {
      const verified = verifyToken(token, process.env.TOTP_SECRET || 'smartfin-dev-totp');
      if (!verified) {
        return res.status(401).json({ status: 'error', errors: ['Invalid 2FA token'] });
      }
    }

    const accessToken = jwt.sign({ userId: 1, email }, JWT_SECRET, { expiresIn: '15m' });

    return res.status(200).json({
      status: 'ok',
      data: { accessToken, tokenType: 'Bearer' },
    });
  } catch (err) {
    return res.status(500).json({ status: 'error', errors: ['Login failed'] });
  }
};

const me = async (req, res) => {
  try {
    return res.status(200).json({
      status: 'ok',
      data: { userId: req.userId },
    });
  } catch (err) {
    return res.status(500).json({ status: 'error', errors: ['Failed to fetch user'] });
  }
};

module.exports = { register, login, me };
