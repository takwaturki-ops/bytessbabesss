
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts'
import { motion } from 'framer-motion'
import {
  LayoutDashboard, Bot, Users, CreditCard, ShieldCheck,
  ChartNoAxesCombined, Mic, Settings, Search, Bell,
  ArrowUpRight, ArrowDownRight, Activity, Menu, X,
  Sparkles, ArrowRight, Zap
} from 'lucide-react'
import './App.css'

// NAVIGATION
const navigation = [
  { name: 'Dashboard', icon: LayoutDashboard },
  { name: 'AI Agents', icon: Bot },
  { name: 'Customers', icon: Users },
  { name: 'Payments', icon: CreditCard },
  { name: 'Security Center', icon: ShieldCheck },
  { name: 'Financial Analytics', icon: ChartNoAxesCombined },
  { name: 'Voice Sales', icon: Mic }
]

// AGENTS DATA
const agents = [
  { name: 'Customer Agent', description: 'Customer interaction & assistance', status: 'Active', color: '#8b5cf6' },
  { name: 'Payment Agent', description: 'Payment processing & validation', status: 'Active', color: '#06b6d4' },
  { name: 'Security Agent', description: 'Fraud detection & protection', status: 'Active', color: '#10b981' },
  { name: 'Financial Agent', description: 'Financial analysis & insights', status: 'Active', color: '#f59e0b' },
  { name: 'Voice Sales Agent', description: 'Voice interaction & sales', status: 'Standby', color: '#ec4899' }
]

// CUSTOMERS DATA
const customers = [
  { name: 'Sarah Johnson', email: 'sarah@gmail.com', initials: 'SJ', orders: 12, spent: '$2,450', status: 'Active' },
  { name: 'Michael Brown', email: 'michael@gmail.com', initials: 'MB', orders: 8, spent: '$1,820', status: 'Active' },
  { name: 'Emma Wilson', email: 'emma@gmail.com', initials: 'EW', orders: 5, spent: '$950', status: 'Inactive' },
  { name: 'David Smith', email: 'david@gmail.com', initials: 'DS', orders: 15, spent: '$3,200', status: 'Active' },
  { name: 'Olivia Davis', email: 'olivia@gmail.com', initials: 'OD', orders: 3, spent: '$420', status: 'Inactive' }
]

function App({ initialDashboard = false }) {
  const navigate = useNavigate()
  const { token } = useAuth()

  const handleDashboardClick = () => {
    setMenuOpen(false)

    if (token) {
      setShowDashboard(true)
    } else {
      navigate('/login')
    }
  }
  const [activePage, setActivePage] = useState('Dashboard')
  const [menuOpen, setMenuOpen] = useState(false)
  const [showDashboard, setShowDashboard] = useState(initialDashboard)

  // LANDING PAGE
  if (!showDashboard) {
    return (
      <motion.div className="landing-page" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8 }}>
        <nav className="landing-nav">
          <div className="landing-logo">
            <div className="landing-logo-icon"><Activity size={25} /></div>
            <span>9antra<span className="logo-dot">.</span></span>
          </div>

          <div className={`landing-nav-links ${menuOpen ? 'open' : ''}`}>
            <a href="#home" onClick={() => setMenuOpen(false)}>Home</a>
            <a href="#agents" onClick={() => setMenuOpen(false)}>Our Agents</a>
            <a href="#about" onClick={() => setMenuOpen(false)}>About</a>
          </div>

          <div className="landing-nav-actions">
            <button className="nav-enter" onClick={handleDashboardClick}>
              Dashboard <ArrowRight size={17} />
            </button>
            <button className="mobile-menu-btn" onClick={() => setMenuOpen(!menuOpen)} aria-label="Toggle navigation">
              {menuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </nav>

        <main className="landing-hero" id="home">
          <div className="hero-glow glow-one"></div>
          <div className="hero-glow glow-two"></div>

          <motion.div className="hero-content" initial={{ opacity: 0, y: 45 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, delay: 0.2 }}>
            <div className="hero-badge"><Sparkles size={15} /> AUTONOMOUS FINTECH INTELLIGENCE</div>
            <h1>The Future of <span>Autonomous Finance.</span></h1>
            <p className="hero-description">
              Meet a new generation of intelligent AI agents.
              Automate financial operations, protect transactions
              and create smarter customer experiences with 9antra.
            </p>
            <div className="hero-buttons">
              <button className="hero-primary" onClick={handleDashboardClick}>
                Explore 9antra <ArrowRight size={19} />
              </button>
              <a href="#agents" className="hero-secondary">Discover our agents</a>
            </div>
            <div className="hero-trust">
              <span><Zap size={16} /> Intelligent</span>
              <span><ShieldCheck size={16} /> Secure</span>
              <span><Activity size={16} /> Autonomous</span>
            </div>
          </motion.div>

          <motion.div className="hero-visual" initial={{ opacity: 0, scale: 0.7, x: 50 }} animate={{ opacity: 1, scale: 1, x: 0 }} transition={{ duration: 1, delay: 0.4 }}>
            <div className="orbit orbit-one"></div>
            <div className="orbit orbit-two"></div>
            <motion.div className="mascot-card" animate={{ y: [0, -15, 0], rotate: [0, 2, 0] }} transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}>
              <div className="mascot-face">
                <img src="/images/9antro.gif" alt="9antro waving hello" className="mascot-gif" />
              </div>
              <div className="mascot-message">
                <strong>Marhb├® bikom ! ­ƒæï</strong>
                <span>I'm 9antro, your AI companion.</span>
              </div>
            </motion.div>
            <div className="floating-tag tag-one"><ShieldCheck size={18} /> AI Security</div>
            <div className="floating-tag tag-two"><Activity size={18} /> Smart Finance</div>
          </motion.div>

          <div className="hero-bottom">
            <span>POWERED BY FIVE AUTONOMOUS AI AGENTS</span>
            <span>SCROLL TO DISCOVER Ôåô</span>
          </div>
        </main>

        <motion.section className="landing-agents" id="agents" initial={{ opacity: 0, y: 50 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.2 }} transition={{ duration: 0.7 }}>
          <span className="section-eyebrow">OUR ECOSYSTEM</span>
          <h2>One team. Five intelligent agents.</h2>
          <p>Designed to work together and make finance smarter.</p>
          <div className="landing-agent-grid">
            {[
              ['Customer Agent', 'Intelligent customer assistance'],
              ['Payment Agent', 'Smart payment processing'],
              ['Security Agent', 'Fraud detection and protection'],
              ['Financial Agent', 'Financial insights and analysis'],
              ['Voice Sales Agent', 'Conversational sales experience']
            ].map(([name, description], index) => (
              <motion.div className="landing-agent-card" key={name} initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: index * 0.12 }} whileHover={{ y: -8, scale: 1.02 }}>
                <div className="agent-number">0{index + 1}</div>
                <Bot size={30} />
                <h3>{name}</h3>
                <p>{description}</p>
              </motion.div>
            ))}
          </div>
        </motion.section>

        <footer className="landing-footer" id="about">
          <strong>9antra.</strong>
          <span>Intelligent. Secure. Autonomous.</span>
          <span>┬® 2026 9antra ┬À FinTech Innovation</span>
        </footer>
      </motion.div>
    )
  }

  // DASHBOARD
  return (
    <div className="app-container">
      <aside className={`sidebar ${menuOpen ? 'open' : ''}`}>
        <div className="brand">
          <div className="brand-icon"><Activity size={25} /></div>
          <div>
            <h2>Autonomous</h2>
            <span>FINTECH TEAM</span>
          </div>
          <button className="close-menu" onClick={() => setMenuOpen(false)}><X /></button>
        </div>

        <div className="workspace">
          <span className="workspace-dot"></span>
          <div>
            <strong>FinTech Workspace</strong>
            <small>Hackathon Project</small>
          </div>
        </div>

        <span className="nav-label">MAIN MENU</span>
        <nav className="navigation">
      {navigation.map((item) => {
        const Icon = item.icon

        return (
          <button
            key={item.name}
            className={`sidebar-link ${activePage === item.name ? 'active' : ''}`}
            onClick={() => setActivePage(item.name)}
          >
            <Icon size={20} />
            <span>{item.name}</span>
          </button>
        )
      })}
        </nav>

        <div className="sidebar-bottom">
          <button className="nav-item"><Settings size={19} /><span>Settings</span></button>
          <div className="profile">
            <div className="avatar">FT</div>
            <div><strong>FinTech Admin</strong><small>Administrator</small></div>
          </div>
        </div>
      </aside>

      {menuOpen && <div className="sidebar-overlay" onClick={() => setMenuOpen(false)} />}

      <main className="main-content">
        <header className="topbar">
          <button className="menu-button" onClick={() => setMenuOpen(true)}><Menu /></button>
          <div className="breadcrumb">
            <span>Workspace</span>
            <span className="breadcrumb-separator">/</span>
            <strong>{activePage}</strong>
          </div>
          <div className="topbar-actions">
            <div className="search-box">
              <Search size={18} />
              <input type="text" placeholder="Search anything..." />
              <kbd>Ôîÿ K</kbd>
            </div>
            <button className="notification-button"><Bell size={20} /><span></span></button>
            <div className="top-avatar">FA</div>
          </div>
        </header>

        {activePage === 'AI Agents' ? (
          <AgentsPage />
        ) : activePage === 'Customers' ? (
          <CustomersPage />
        ) : activePage === 'Payments' ? (
          <PaymentsPage />
        ) : activePage === 'Security Center' ? (
          <SecurityPage />
        ) : activePage === 'Financial Analytics' ? (
          <FinancialPage />
        ) : activePage === 'Voice Sales' ? (
          <VoiceSalesPage />
        ) : (
          <DashboardPage setActivePage={setActivePage} />
        )}
      </main>
    </div>
  )
}

// DASHBOARD HOME
function DashboardPage({ setActivePage }) {
  return (
    <div className="dashboard-content">
      <section className="welcome-section">
        <div>
          <span className="welcome-label">OVERVIEW</span>
          <h1>Welcome back, <span>Admin</span> ­ƒæï</h1>
          <p>Here's what's happening with your autonomous FinTech team today.</p>
        </div>
        <div className="date-badge"><Activity size={16} /> System operational</div>
      </section>

      <section className="stats-grid">
        <StatCard title="Total Interactions" value="2,840" change="+12.8%" positive icon={<Users />} color="purple" />
        <StatCard title="Successful Payments" value="1,429" change="+8.2%" positive icon={<CreditCard />} color="cyan" />
        <StatCard title="Conversion Rate" value="68.4%" change="+5.4%" positive icon={<ChartNoAxesCombined />} color="green" />
        <StatCard title="Security Alerts" value="12" change="-3.1%" positive icon={<ShieldCheck />} color="orange" />
      </section>

      <section className="content-grid">
        <div className="panel agents-panel">
          <div className="panel-header">
            <div><h2>AI Agents Overview</h2><p>Monitor your autonomous team</p></div>
            <button className="view-all" onClick={() => setActivePage('AI Agents')}>View all <ArrowUpRight size={15} /></button>
          </div>
          <div className="agents-list">
            {agents.map(agent => (
              <div className="agent-row" key={agent.name}>
                <div className="agent-icon" style={{ '--agent-color': agent.color }}><Bot size={21} /></div>
                <div className="agent-info"><strong>{agent.name}</strong><small>{agent.description}</small></div>
                <span className={`agent-status ${agent.status === 'Active' ? 'status-active' : 'status-standby'}`}><span></span>{agent.status}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="panel activity-panel">
          <div className="panel-header">
            <div><h2>System Activity</h2><p>Real-time system overview</p></div>
            <span className="live-badge"><span></span> Live</span>
          </div>
          <div className="activity-score">
            <div className="score-circle"><div><strong>98<span>%</span></strong><small>System health</small></div></div>
          </div>
          <div className="activity-details">
            <div><span>Agent availability</span><strong>4 / 5</strong></div>
            <div><span>API response time</span><strong>124 ms</strong></div>
            <div><span>Active processes</span><strong>28</strong></div>
          </div>
        </div>
      </section>

      <section className="panel transactions-panel">
        <div className="panel-header">
          <div><h2>Recent Transactions</h2><p>Latest simulated payment activity</p></div>
          <button className="view-all" onClick={() => setActivePage('Payments')}>View all <ArrowUpRight size={15} /></button>
        </div>
        <div className="table-wrapper">
          <table>
            <thead><tr><th>Transaction ID</th><th>Customer</th><th>Amount</th><th>Date</th><th>Status</th></tr></thead>
            <tbody>
              <Transaction id="TXN-2026-001" customer="Sarah Johnson" amount="$2,450.00" date="Nov 08, 2026" status="Completed" />
              <Transaction id="TXN-2026-002" customer="Michael Chen" amount="$890.50" date="Nov 08, 2026" status="Pending" />
              <Transaction id="TXN-2026-003" customer="Emma Wilson" amount="$1,200.00" date="Nov 07, 2026" status="Completed" />
              <Transaction id="TXN-2026-004" customer="James Brown" amount="$450.00" date="Nov 07, 2026" status="Failed" />
            </tbody>
          </table>
        </div>
        <p className="demo-note">Demo environment ┬À All displayed data is simulated</p>
      </section>

      <footer className="dashboard-footer">
        <span>┬® 2026 Autonomous FinTech Team</span>
        <span>Built for innovation <span className="heart">ÔÖÑ</span></span>
      </footer>
    </div>
  )
}

// AI AGENTS PAGE
function AgentsPage() {
  const [selectedFilter, setSelectedFilter] = useState('All')
  const filters = ['All', 'Active', 'Standby']
  const filteredAgents = agents.filter(agent => selectedFilter === 'All' || agent.status === selectedFilter)

  return (
    <div className="dashboard-content">
      <motion.section className="welcome-section" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <div>
          <span className="welcome-label">AUTONOMOUS TEAM</span>
          <h1>AI Agents <span>Overview</span> ­ƒñû</h1>
          <p>Manage and monitor your intelligent financial agents.</p>
        </div>
        <div className="date-badge"><Activity size={16} /> System operational</div>
      </motion.section>

      <section className="stats-grid">
        <StatCard title="Total Agents" value="5" change="All agents" positive icon={<Bot />} color="purple" />
        <StatCard title="Active Agents" value="4" change="80% availability" positive icon={<Activity />} color="green" />
        <StatCard title="On Standby" value="1" change="Monitoring" positive icon={<ShieldCheck />} color="orange" />
      </section>

      <section className="panel agents-panel">
        <div className="panel-header">
          <div><h2>Your AI Team</h2><p>Explore and monitor each agent.</p></div>
        </div>
        <div className="agent-filters">
          {filters.map(filter => (
            <button key={filter} className={`agent-filter ${selectedFilter === filter ? 'active' : ''}`} onClick={() => setSelectedFilter(filter)}>{filter}</button>
          ))}
        </div>
        <div className="agents-list">
          {filteredAgents.map((agent, index) => (
            <motion.div className="agent-row" key={agent.name} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.1 }}>
              <div className="agent-icon" style={{ '--agent-color': agent.color }}><Bot size={22} /></div>
              <div className="agent-info"><strong>{agent.name}</strong><small>{agent.description}</small></div>
              <span className={`agent-status ${agent.status === 'Active' ? 'status-active' : 'status-standby'}`}><span></span>{agent.status}</span>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  )
}

// CUSTOMERS PAGE
function CustomersPage() {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('All')

  const filteredCustomers = customers.filter(customer => {
    const matchesSearch = customer.name.toLowerCase().includes(search.toLowerCase()) ||
      customer.email.toLowerCase().includes(search.toLowerCase())
    const matchesFilter = filter === 'All' || customer.status === filter
    return matchesSearch && matchesFilter
  })

  return (
    <div className="dashboard-content">
      <motion.section className="welcome-section" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <div>
          <span className="welcome-label">CUSTOMER MANAGEMENT</span>
          <h1>Our <span>Customers</span> ­ƒæÑ</h1>
          <p>Manage your customer relationships and activity.</p>
        </div>
        <div className="date-badge"><Users size={16} /> Customer overview</div>
      </motion.section>

      <section className="stats-grid">
        <StatCard title="Total Customers" value="5" change="Registered customers" positive icon={<Users />} color="purple" />
        <StatCard title="Active Customers" value="3" change="60% of total" positive icon={<Activity />} color="green" />
        <StatCard title="Inactive Customers" value="2" change="Need attention" positive icon={<ShieldCheck />} color="orange" />
      </section>

      <section className="panel">
        <div className="panel-header">
          <div><h2>Customer Directory</h2><p>Search and monitor your customers.</p></div>
          <span>{filteredCustomers.length} customers</span>
        </div>

        <div className="customer-search">
          <Search size={18} />
          <input type="text" placeholder="Search by name or email..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>

        <div className="agent-filters">
          {['All', 'Active', 'Inactive'].map(value => (
            <button key={value} className={`agent-filter ${filter === value ? 'active' : ''}`} onClick={() => setFilter(value)}>{value}</button>
          ))}
        </div>

        <div className="table-wrapper">
          <table>
            <thead><tr><th>Customer</th><th>Orders</th><th>Total Spent</th><th>Status</th></tr></thead>
            <tbody>
              {filteredCustomers.map(customer => (
                <tr key={customer.email}>
                  <td>
                    <div className="customer-cell">
                      <div className="customer-avatar">{customer.initials}</div>
                      <div><strong>{customer.name}</strong><small>{customer.email}</small></div>
                    </div>
                  </td>
                  <td>{customer.orders}</td>
                  <td>{customer.spent}</td>
                  <td><span className={`agent-status ${customer.status === 'Active' ? 'status-active' : 'status-standby'}`}><span></span>{customer.status}</span></td>
                </tr>
              ))}
              {filteredCustomers.length === 0 && <tr><td colSpan="4">No customers found.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

// STAT CARD
function StatCard({ title, value, change, positive, icon, color }) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        <div className={`stat-icon ${color}`}>{icon}</div>
        <span className={`stat-change ${positive ? 'positive' : 'negative'}`}>
          {positive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
          {change}
        </span>
      </div>
      <p>{title}</p>
      <h2>{value}</h2>
      <span className="stat-caption">Compared to last month</span>
    </div>
  )
}

// TRANSACTION
function Transaction({ id, customer, amount, date, status }) {
  return (
    <tr>
      <td className="transaction-id">{id}</td>
      <td>{customer}</td>
      <td className="transaction-amount">{amount}</td>
      <td>{date}</td>
      <td><span className={`transaction-status ${status.toLowerCase()}`}>{status}</span></td>
    </tr>
  )
}
function PaymentsPage() {
  const [filter, setFilter] = useState('All')
  const [search, setSearch] = useState('')

  const payments = [
    { id: 'PAY-001', customer: 'Sarah Johnson', email: 'sarah@gmail.com', amount: 450, method: 'Credit Card', status: 'Successful', date: '08 Nov 2026' },
    { id: 'PAY-002', customer: 'Michael Brown', email: 'michael@gmail.com', amount: 120, method: 'PayPal', status: 'Pending', date: '08 Nov 2026' },
    { id: 'PAY-003', customer: 'Emma Wilson', email: 'emma@gmail.com', amount: 320, method: 'Bank Transfer', status: 'Failed', date: '07 Nov 2026' },
    { id: 'PAY-004', customer: 'David Smith', email: 'david@gmail.com', amount: 890, method: 'Credit Card', status: 'Successful', date: '07 Nov 2026' },
    { id: 'PAY-005', customer: 'Olivia Davis', email: 'olivia@gmail.com', amount: 75, method: 'PayPal', status: 'Successful', date: '06 Nov 2026' },
    { id: 'PAY-006', customer: 'James Wilson', email: 'james@gmail.com', amount: 210, method: 'Credit Card', status: 'Pending', date: '06 Nov 2026' },
  ]

  const filteredPayments = payments.filter((payment) => {
    const matchesFilter = filter === 'All' || payment.status === filter
    const matchesSearch =
      payment.customer.toLowerCase().includes(search.toLowerCase()) ||
      payment.id.toLowerCase().includes(search.toLowerCase())

    return matchesFilter && matchesSearch
  })

  const successful = payments.filter(p => p.status === 'Successful').length
  const pending = payments.filter(p => p.status === 'Pending').length
  const failed = payments.filter(p => p.status === 'Failed').length
  const total = payments
    .filter(p => p.status === 'Successful')
    .reduce((sum, p) => sum + p.amount, 0)

  return (
    <div className="page-content">
      <div className="page-heading">
        <div>
          <h1>Payments</h1>
          <p>Monitor and manage all your transactions.</p>
        </div>
        <button className="primary-btn">
          <CreditCard size={17} /> Manage Payments
        </button>
      </div>

      <div className="stats-grid">
        <StatCard
          title="Total Revenue"
          value={`$${total.toLocaleString()}`}
          change="From successful payments"
          icon={<CreditCard size={22} />}
          color="blue"
        />
        <StatCard
          title="Successful"
          value={successful}
          change="Completed transactions"
          icon={<Activity size={22} />}
          color="green"
        />
        <StatCard
          title="Pending"
          value={pending}
          change="Awaiting confirmation"
          icon={<Activity size={22} />}
          color="orange"
        />
        <StatCard
          title="Failed"
          value={failed}
          change="Unsuccessful transactions"
          icon={<ShieldCheck size={22} />}
          color="red"
        />
      </div>

      <div className="content-card">
        <div className="section-header">
          <div>
            <h2>Recent Transactions</h2>
            <p>Review and track payment activity.</p>
          </div>
          <div className="customer-search">
            <Search size={17} />
            <input
              type="text"
              placeholder="Search by customer or ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="agent-filters">
          {['All', 'Successful', 'Pending', 'Failed'].map((status) => (
            <button
              key={status}
              className={`agent-filter ${filter === status ? 'active' : ''}`}
              onClick={() => setFilter(status)}
            >
              {status}
            </button>
          ))}
        </div>

        <div className="table-wrapper">
          <table className="transactions-table">
            <thead>
              <tr>
                <th>Transaction ID</th>
                <th>Customer</th>
                <th>Amount</th>
                <th>Payment Method</th>
                <th>Date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredPayments.map((payment) => (
                <tr key={payment.id}>
                  <td><strong>{payment.id}</strong></td>
                  <td>
                    <div className="customer-cell">
                      <div className="customer-avatar">
                        {payment.customer.split(' ').map(n => n[0]).join('')}
                      </div>
                      <div>
                        <strong>{payment.customer}</strong>
                        <small>{payment.email}</small>
                      </div>
                    </div>
                  </td>
                  <td><strong>${payment.amount.toLocaleString()}</strong></td>
                  <td>{payment.method}</td>
                  <td>{payment.date}</td>
                  <td>
                    <span className={`status-badge ${payment.status.toLowerCase()}`}>
                      {payment.status}
                    </span>
                  </td>
                </tr>
              ))}
              {filteredPayments.length === 0 && (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: '30px' }}>
                    No payments found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
function SecurityPage() {
  const [filter, setFilter] = useState('All')

  const incidents = [
    { id: 'SEC-001', title: 'Suspicious login attempt', source: 'Unknown IP address', severity: 'Critical', status: 'Blocked', time: '08 Nov 2026, 10:42' },
    { id: 'SEC-002', title: 'Multiple failed payments', source: 'Payment Agent', severity: 'High', status: 'Investigating', time: '08 Nov 2026, 09:30' },
    { id: 'SEC-003', title: 'Unusual API activity', source: 'API Gateway', severity: 'Medium', status: 'Monitoring', time: '08 Nov 2026, 08:15' },
    { id: 'SEC-004', title: 'Potential phishing attempt', source: 'Email System', severity: 'High', status: 'Blocked', time: '07 Nov 2026, 16:20' },
    { id: 'SEC-005', title: 'New device detected', source: 'Customer Account', severity: 'Low', status: 'Resolved', time: '07 Nov 2026, 14:05' },
  ]

  const filteredIncidents = incidents.filter((incident) =>
    filter === 'All' || incident.severity === filter
  )

  const critical = incidents.filter(i => i.severity === 'Critical').length
  const high = incidents.filter(i => i.severity === 'High').length
  const medium = incidents.filter(i => i.severity === 'Medium').length
  const low = incidents.filter(i => i.severity === 'Low').length

  return (
    <div className="page-content">
      <div className="page-heading">
        <div>
          <h1>Security Center</h1>
          <p>Monitor threats and protect your financial ecosystem.</p>
        </div>
        <span className="status-badge active">ÔùÅ System Protected</span>
      </div>

      <div className="stats-grid">
        <StatCard
          title="Total Incidents"
          value={incidents.length}
          change="Detected security events"
          icon={<ShieldCheck size={22} />}
          color="blue"
        />
        <StatCard
          title="Critical Threats"
          value={critical}
          change="Require immediate attention"
          icon={<ShieldCheck size={22} />}
          color="red"
        />
        <StatCard
          title="High Severity"
          value={high}
          change="Potential security risks"
          icon={<Activity size={22} />}
          color="orange"
        />
        <StatCard
          title="Low / Medium"
          value={medium + low}
          change="Under monitoring"
          icon={<Activity size={22} />}
          color="green"
        />
      </div>

      <div className="content-card">
        <div className="section-header">
          <div>
            <h2>Threat Overview</h2>
            <p>Current security incidents and detected activities.</p>
          </div>
          <span className="status-badge active">Protection Active</span>
        </div>

        <div className="agent-filters">
          {['All', 'Critical', 'High', 'Medium', 'Low'].map((severity) => (
            <button
              key={severity}
              className={`agent-filter ${filter === severity ? 'active' : ''}`}
              onClick={() => setFilter(severity)}
            >
              {severity}
            </button>
          ))}
        </div>

        <div className="table-wrapper">
          <table className="transactions-table">
            <thead>
              <tr>
                <th>Incident</th>
                <th>Source</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Detected At</th>
              </tr>
            </thead>
            <tbody>
              {filteredIncidents.map((incident) => (
                <tr key={incident.id}>
                  <td>
                    <strong>{incident.title}</strong>
                    <small style={{ display: 'block', color: '#94a3b8' }}>
                      {incident.id}
                    </small>
                  </td>
                  <td>{incident.source}</td>
                  <td>
                    <span className={`status-badge ${incident.severity.toLowerCase()}`}>
                      {incident.severity}
                    </span>
                  </td>
                  <td>
                    <span className={`status-badge ${incident.status.toLowerCase()}`}>
                      {incident.status}
                    </span>
                  </td>
                  <td>{incident.time}</td>
                </tr>
              ))}
              {filteredIncidents.length === 0 && (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '30px' }}>
                    No incidents found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="content-card security-tip">
        <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
          <ShieldCheck size={30} color="#10b981" />
          <div>
            <h3>Security Recommendation</h3>
            <p>Keep monitoring unusual login attempts and review high-severity incidents regularly.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
function FinancialPage() {
  const [period, setPeriod] = useState('Monthly')

  const monthlyData = [
    { month: 'Jan', revenue: 4200, expenses: 2400 },
    { month: 'Feb', revenue: 5100, expenses: 2800 },
    { month: 'Mar', revenue: 4600, expenses: 2600 },
    { month: 'Apr', revenue: 6200, expenses: 3100 },
    { month: 'May', revenue: 5800, expenses: 2900 },
    { month: 'Jun', revenue: 7500, expenses: 3500 },
  ]

  const quarterlyData = [
    { month: 'Q1', revenue: 13900, expenses: 7800 },
    { month: 'Q2', revenue: 19500, expenses: 9500 },
    { month: 'Q3', revenue: 16800, expenses: 8200 },
    { month: 'Q4', revenue: 22100, expenses: 11000 },
  ]

  const data = period === 'Monthly' ? monthlyData : quarterlyData
  const totalRevenue = data.reduce((sum, item) => sum + item.revenue, 0)
  const totalExpenses = data.reduce((sum, item) => sum + item.expenses, 0)
  const profit = totalRevenue - totalExpenses

  return (
    <div className="page-content">
      <div className="page-heading">
        <div>
          <h1>Financial Analytics</h1>
          <p>Track revenue, expenses and financial performance.</p>
        </div>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          style={{
            padding: '11px 16px',
            border: '1px solid #dce8f8',
            borderRadius: '10px',
            background: 'white',
            color: '#155ac1',
            fontWeight: 600
          }}
        >
          <option>Monthly</option>
          <option>Quarterly</option>
        </select>
      </div>

      <div className="stats-grid">
        <StatCard
          title="Total Revenue"
          value={`$${totalRevenue.toLocaleString()}`}
          change="Total generated revenue"
          icon={<CreditCard size={22} />}
          color="blue"
        />
        <StatCard
          title="Total Expenses"
          value={`$${totalExpenses.toLocaleString()}`}
          change="Operational expenses"
          icon={<ArrowDownRight size={22} />}
          color="orange"
        />
        <StatCard
          title="Net Profit"
          value={`$${profit.toLocaleString()}`}
          change="Revenue minus expenses"
          icon={<ArrowUpRight size={22} />}
          color="green"
        />
        <StatCard
          title="Profit Margin"
          value={`${((profit / totalRevenue) * 100).toFixed(1)}%`}
          change="Net profit percentage"
          icon={<ChartNoAxesCombined size={22} />}
          color="purple"
        />
      </div>

      <div className="content-card">
        <div className="section-header">
          <div>
            <h2>Revenue & Expenses</h2>
            <p>Compare your financial performance over time.</p>
          </div>
          <span className="status-badge active">{period} Overview</span>
        </div>

        <div style={{ width: '100%', height: 320, marginTop: 25 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} barGap={8}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e8eef7" />
              <XAxis dataKey="month" axisLine={false} tickLine={false} />
              <YAxis axisLine={false} tickLine={false} />
              <Tooltip />
              <Legend />
              <Bar dataKey="revenue" name="Revenue" fill="#2563eb" radius={[6, 6, 0, 0]} />
              <Bar dataKey="expenses" name="Expenses" fill="#f59e0b" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="content-card">
        <div className="section-header">
          <div>
            <h2>Financial Breakdown</h2>
            <p>Detailed revenue and expense summary.</p>
          </div>
        </div>

        <div className="table-wrapper">
          <table className="transactions-table">
            <thead>
              <tr>
                <th>Period</th>
                <th>Revenue</th>
                <th>Expenses</th>
                <th>Net Profit</th>
                <th>Profit Margin</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item) => {
                const net = item.revenue - item.expenses
                const margin = (net / item.revenue) * 100

                return (
                  <tr key={item.month}>
                    <td><strong>{item.month}</strong></td>
                    <td>${item.revenue.toLocaleString()}</td>
                    <td>${item.expenses.toLocaleString()}</td>
                    <td style={{ color: '#10b981', fontWeight: 700 }}>
                      ${net.toLocaleString()}
                    </td>
                    <td>{margin.toFixed(1)}%</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}


function VoiceSalesPage() {
  const [filter, setFilter] = useState('All')

  const calls = [
    { id: 'CALL-001', customer: 'Sarah Johnson', agent: 'Sales Agent', duration: '04:32', result: 'Sale Completed', amount: 450, status: 'Completed', time: '10:42 AM' },
    { id: 'CALL-002', customer: 'Michael Brown', agent: 'Customer Agent', duration: '02:15', result: 'Product Inquiry', amount: 0, status: 'Completed', time: '10:15 AM' },
    { id: 'CALL-003', customer: 'Emma Wilson', agent: 'Sales Agent', duration: '00:45', result: 'No Answer', amount: 0, status: 'Missed', time: '09:50 AM' },
    { id: 'CALL-004', customer: 'David Smith', agent: 'Sales Agent', duration: '06:18', result: 'Sale Completed', amount: 890, status: 'Completed', time: '09:20 AM' },
    { id: 'CALL-005', customer: 'Olivia Davis', agent: 'Customer Agent', duration: '01:12', result: 'Call in progress', amount: 0, status: 'In Progress', time: '09:05 AM' },
    { id: 'CALL-006', customer: 'James Wilson', agent: 'Sales Agent', duration: '03:40', result: 'Sale Completed', amount: 210, status: 'Completed', time: 'Yesterday' },
  ]

  const filteredCalls = calls.filter(call =>
    filter === 'All' || call.status === filter
  )

  const completed = calls.filter(c => c.status === 'Completed').length
  const missed = calls.filter(c => c.status === 'Missed').length
  const revenue = calls.reduce((sum, c) => sum + c.amount, 0)
  const sales = calls.filter(c => c.amount > 0).length
  const conversion = completed ? (sales / completed) * 100 : 0

  return (
    <div className="page-content">
      <div className="page-heading">
        <div>
          <h1>Voice Sales</h1>
          <p>Manage AI-powered voice interactions and sales performance.</p>
        </div>
        <span className="status-badge active">
          <Activity size={14} /> Voice Agents Online
        </span>
      </div>

      <div className="stats-grid">
        <StatCard
          title="Total Calls"
          value={calls.length}
          change="Recorded interactions"
          icon={<Mic size={22} />}
          color="blue"
        />
        <StatCard
          title="Completed Calls"
          value={completed}
          change="Successfully completed"
          icon={<Activity size={22} />}
          color="green"
        />
        <StatCard
          title="Sales Revenue"
          value={`$${revenue.toLocaleString()}`}
          change="Generated by voice agents"
          icon={<CreditCard size={22} />}
          color="purple"
        />
        <StatCard
          title="Conversion Rate"
          value={`${conversion.toFixed(1)}%`}
          change={`${sales} successful sales`}
          icon={<ChartNoAxesCombined size={22} />}
          color="orange"
        />
      </div>

      <div className="content-card">
        <div className="section-header">
          <div>
            <h2>Voice Agent Performance</h2>
            <p>Overview of your AI voice sales activity.</p>
          </div>
        </div>

        <div className="voice-agent-grid">
          <div className="voice-agent-card">
            <div className="voice-icon">
              <Mic size={24} />
            </div>
            <div>
              <h3>Sales Voice Agent</h3>
              <p>Handles customer calls and sales.</p>
              <span className="status-badge active">Active</span>
            </div>
          </div>

          <div className="voice-agent-card">
            <div className="voice-icon">
              <Bot size={24} />
            </div>
            <div>
              <h3>Customer Support Agent</h3>
              <p>Answers questions and assists customers.</p>
              <span className="status-badge active">Active</span>
            </div>
          </div>
        </div>
      </div>

      <div className="content-card">
        <div className="section-header">
          <div>
            <h2>Call History</h2>
            <p>Track recent conversations and sales results.</p>
          </div>
        </div>

        <div className="agent-filters">
          {['All', 'Completed', 'In Progress', 'Missed'].map(status => (
            <button
              key={status}
              className={`agent-filter ${filter === status ? 'active' : ''}`}
              onClick={() => setFilter(status)}
            >
              {status}
            </button>
          ))}
        </div>

        <div className="table-wrapper">
          <table className="transactions-table">
            <thead>
              <tr>
                <th>Call ID</th>
                <th>Customer</th>
                <th>AI Agent</th>
                <th>Duration</th>
                <th>Result</th>
                <th>Revenue</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredCalls.map(call => (
                <tr key={call.id}>
                  <td><strong>{call.id}</strong></td>
                  <td>{call.customer}</td>
                  <td>{call.agent}</td>
                  <td>{call.duration}</td>
                  <td>{call.result}</td>
                  <td>
                    <strong>
                      {call.amount ? `$${call.amount.toLocaleString()}` : 'ÔÇö'}
                    </strong>
                  </td>
                  <td>
                    <span className={`status-badge ${
                      call.status === 'Completed'
                        ? 'active'
                        : call.status === 'Missed'
                        ? 'failed'
                        : 'pending'
                    }`}>
                      {call.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
export default App
