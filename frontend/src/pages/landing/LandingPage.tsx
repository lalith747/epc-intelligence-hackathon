import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { motion } from 'framer-motion'
import { ArrowRight, BarChart3, Shield, Zap, Users, TrendingUp } from 'lucide-react'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-orange-600/10 via-background to-background" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-orange-600/20 rounded-full blur-[120px]" />
        
        <div className="relative container mx-auto px-6 py-20 lg:py-32">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center max-w-4xl mx-auto"
          >
            <h1 className="text-5xl lg:text-7xl font-bold mb-6">
              <span className="text-gradient">AI PROJECT</span>
              <br />
              <span className="text-foreground">MONITORING &</span>
              <br />
              <span className="text-gradient">RISK ENGINE</span>
            </h1>
            
            <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
              Autonomous AI that predicts project delays before they happen. 
              Transform how you manage Data Centre EPC Projects with intelligent, 
              real-time insights and proactive risk mitigation.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button size="lg" className="orange-glow text-lg px-8" asChild>
                <Link to="/register">
                  Get Started
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" className="text-lg px-8" asChild>
                <Link to="/login">Sign In</Link>
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 container mx-auto px-6">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl font-bold mb-4">Enterprise-Grade AI Capabilities</h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Six autonomous AI agents working together to monitor, analyze, and protect your projects
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
              className="glass-card p-6 rounded-xl hover:orange-glow transition-all duration-300"
            >
              <div className="w-12 h-12 rounded-lg bg-orange-600/20 flex items-center justify-center mb-4">
                <feature.icon className="w-6 h-6 text-orange-600" />
              </div>
              <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
              <p className="text-muted-foreground">{feature.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 container mx-auto px-6">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="glass-card rounded-2xl p-12 text-center orange-glow"
        >
          <h2 className="text-4xl font-bold mb-4">Ready to Transform Your Project Management?</h2>
          <p className="text-muted-foreground text-lg mb-8 max-w-2xl mx-auto">
            Join leading construction companies using AI to deliver projects on time and on budget
          </p>
          <Button size="lg" className="text-lg px-8" asChild>
            <Link to="/register">
              Start Free Trial
              <ArrowRight className="ml-2 w-5 h-5" />
            </Link>
          </Button>
        </motion.div>
      </section>
    </div>
  )
}

const features = [
  {
    icon: BarChart3,
    title: 'Schedule Intelligence',
    description: 'AI-powered schedule analysis with critical path detection and delay prediction'
  },
  {
    icon: Shield,
    title: 'Risk Assessment',
    description: 'Continuous risk monitoring with probability, impact, and confidence scoring'
  },
  {
    icon: Zap,
    title: 'Smart Recommendations',
    description: 'Actionable recommendations with expected impact and estimated days saved'
  },
  {
    icon: Users,
    title: 'Procurement Monitoring',
    description: 'Track suppliers, materials, and deliveries with predictive shortage alerts'
  },
  {
    icon: TrendingUp,
    title: 'Executive Insights',
    description: 'Automated daily and weekly summaries with root cause analysis'
  },
  {
    icon: BarChart3,
    title: 'AI Assistant',
    description: 'Natural language interface to query project data and get instant answers'
  }
]
