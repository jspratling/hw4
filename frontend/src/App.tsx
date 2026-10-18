import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import './App.css'
import './storefront.css'
import { AuthProvider } from './auth'
import { CartProvider } from './cart'
import { ChatResultsProvider } from './chatResults'
import ChatWidget from './components/ChatWidget'
import NavBar from './components/NavBar'
import SiteFooter from './components/SiteFooter'
import SpiritBar from './components/SpiritBar'
import AboutPage from './pages/AboutPage'
import CartPage from './pages/CartPage'
import CheckoutPage from './pages/CheckoutPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import ProductDetailPage from './pages/ProductDetailPage'
import ProductsPage from './pages/ProductsPage'
import RegisterPage from './pages/RegisterPage'

function NotFoundPage() {
  return (
    <main className="page narrow">
      <h1>Page not found</h1>
      <p>
        <Link to="/">Go back home</Link>
      </p>
    </main>
  )
}

function App() {
  return (
    <AuthProvider>
      <CartProvider>
      <ChatResultsProvider>
      <BrowserRouter>
        <SpiritBar />
        <NavBar />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/products/:productId" element={<ProductDetailPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/cart" element={<CartPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
        <SiteFooter />
        <ChatWidget />
      </BrowserRouter>
      </ChatResultsProvider>
      </CartProvider>
    </AuthProvider>
  )
}

export default App
