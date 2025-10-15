import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Clock, CheckCircle, TrendingUp, Cpu, Globe, Code, Database, Zap, Users, Award, BarChart, Activity, Layers, AlertCircle, Github, Play } from 'lucide-react';

const Presentation = () => {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  // Animation styles as JS objects
  const animationStyles = {
    fadeIn: {
      animation: 'fadeIn 0.6s ease-in forwards'
    },
    slideUp: {
      animation: 'slideUp 0.6s ease-out forwards'
    },
    slideLeft: {
      animation: 'slideLeft 0.6s ease-out forwards'
    },
    slideRight: {
      animation: 'slideRight 0.6s ease-out forwards'
    },
    scaleIn: {
      animation: 'scaleIn 0.6s ease-out forwards'
    }
  };

  const slides = [
    // Slide 1: Title
    {
      title: "Smart Support",
      subtitle: "AI-Powered Customer Support Automation",
      content: (
        <div className="flex flex-col items-center justify-center h-full bg-gradient-to-br from-blue-600 via-blue-700 to-green-600 text-white p-12">
          <div className="mb-8">
            <Cpu className="w-32 h-32 text-white/90" />
          </div>
          <h1 className="text-7xl font-bold mb-4">Smart Support</h1>
          <h2 className="text-3xl mb-8 text-blue-100">AI-Powered Customer Support Automation</h2>
          <div className="text-xl text-blue-200">
            Intelligent Classification & Template Recommendation System
          </div>
          <div className="mt-12 text-lg text-blue-200">
            Minsk Hackathon 2025 • Team Smart Support
          </div>
        </div>
      )
    },
    
    // Slide 2: The Problem
    {
      title: "The Problem",
      content: (
        <div className="p-12 bg-gradient-to-br from-red-50 to-orange-50 h-full">
          <h2 className="text-5xl font-bold mb-12 text-red-800">The Challenge</h2>
          
          <div className="space-y-8">
            <div className="flex items-start space-x-6">
              <AlertCircle className="w-12 h-12 text-red-600 flex-shrink-0 mt-2" />
              <div>
                <h3 className="text-2xl font-semibold mb-2">Manual Template Search</h3>
                <p className="text-xl text-gray-700">Support operators manually search through 200+ FAQ templates</p>
              </div>
            </div>
            
            <div className="flex items-start space-x-6">
              <Clock className="w-12 h-12 text-orange-600 flex-shrink-0 mt-2" />
              <div>
                <h3 className="text-2xl font-semibold mb-2">Slow Response Times</h3>
                <p className="text-xl text-gray-700">Current process takes 5-10 minutes per customer inquiry</p>
              </div>
            </div>
            
            <div className="flex items-start space-x-6">
              <Users className="w-12 h-12 text-yellow-600 flex-shrink-0 mt-2" />
              <div>
                <h3 className="text-2xl font-semibold mb-2">Inconsistent Quality</h3>
                <p className="text-xl text-gray-700">Manual classification leads to inconsistent categorization</p>
              </div>
            </div>
          </div>
          
          <div className="mt-12 p-6 bg-red-100 rounded-lg">
            <div className="text-3xl font-bold text-red-800">
              Cost of Inefficiency: 90% of operator time wasted on searching
            </div>
          </div>
        </div>
      )
    },
    
    // Slide 3: Our Solution
    {
      title: "Our Solution",
      content: (
        <div className="p-12 bg-gradient-to-br from-green-50 to-blue-50 h-full">
          <h2 className="text-5xl font-bold mb-12 text-green-800">Smart Support Solution</h2>
          
          <div className="grid grid-cols-2 gap-8">
            <div className="space-y-6">
              <div>
                <div className="flex items-center space-x-4 mb-3">
                  <Cpu className="w-8 h-8 text-blue-600" />
                  <h3 className="text-2xl font-semibold">AI-Powered Classification</h3>
                </div>
                <p className="text-lg text-gray-700">Automatic analysis and categorization of customer inquiries</p>
              </div>
              
              <div>
                <div className="flex items-center space-x-4 mb-3">
                  <Zap className="w-8 h-8 text-green-600" />
                  <h3 className="text-2xl font-semibold">Intelligent Recommendations</h3>
                </div>
                <p className="text-lg text-gray-700">Semantic search finds the most relevant templates instantly</p>
              </div>
              
              <div>
                <div className="flex items-center space-x-4 mb-3">
                  <Activity className="w-8 h-8 text-purple-600" />
                  <h3 className="text-2xl font-semibold">Real-Time Interface</h3>
                </div>
                <p className="text-lg text-gray-700">One-click template selection and response sending</p>
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow-lg p-8">
              <div className="text-center">
                <div className="text-6xl font-bold text-green-600 mb-4">3.3s</div>
                <div className="text-xl text-gray-600">End-to-End Response Time</div>
                <div className="mt-6 text-sm text-gray-500">vs. 5-10 minutes manually</div>
                <div className="mt-8">
                  <div className="text-4xl font-bold text-blue-600">95%</div>
                  <div className="text-lg text-gray-600">Faster Response</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )
    },
    
    // Slide 4: System Architecture
    {
      title: "System Architecture",
      content: (
        <div className="p-12 bg-gradient-to-br from-gray-50 to-blue-50 h-full">
          <h2 className="text-5xl font-bold mb-12 text-gray-800">Three Core Modules</h2>
          
          <div className="grid grid-cols-3 gap-8">
            <div className="bg-blue-600 text-white rounded-lg p-6 shadow-lg">
              <Cpu className="w-12 h-12 mb-4" />
              <h3 className="text-xl font-bold mb-3">Classification Module</h3>
              <ul className="space-y-2 text-sm">
                <li>• Qwen2.5-72B LLM</li>
                <li>• Intent analysis</li>
                <li>• Category detection</li>
                <li>• 95% accuracy</li>
              </ul>
            </div>
            
            <div className="bg-green-600 text-white rounded-lg p-6 shadow-lg">
              <Database className="w-12 h-12 mb-4" />
              <h3 className="text-xl font-bold mb-3">Ranking Module</h3>
              <ul className="space-y-2 text-sm">
                <li>• BGE-M3 embeddings</li>
                <li>• 1024-dim vectors</li>
                <li>• Semantic search</li>
                <li>• 93% top-3 accuracy</li>
              </ul>
            </div>
            
            <div className="bg-purple-600 text-white rounded-lg p-6 shadow-lg">
              <Globe className="w-12 h-12 mb-4" />
              <h3 className="text-xl font-bold mb-3">Operator Interface</h3>
              <ul className="space-y-2 text-sm">
                <li>• React + TypeScript</li>
                <li>• Real-time updates</li>
                <li>• One-click responses</li>
                <li>• Professional UI/UX</li>
              </ul>
            </div>
          </div>
          
          <div className="mt-12 bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-2xl font-bold mb-4">Data Flow Pipeline</h3>
            <div className="flex items-center justify-center space-x-4 text-lg">
              <div className="bg-gray-100 px-4 py-2 rounded">Customer Inquiry</div>
              <ChevronRight className="text-gray-400" />
              <div className="bg-blue-100 px-4 py-2 rounded">AI Classification</div>
              <ChevronRight className="text-gray-400" />
              <div className="bg-green-100 px-4 py-2 rounded">Template Retrieval</div>
              <ChevronRight className="text-gray-400" />
              <div className="bg-purple-100 px-4 py-2 rounded">Operator Response</div>
            </div>
          </div>
        </div>
      )
    },
    
    // Slide 5: Live Demo Walkthrough
    {
      title: "Live Demo",
      content: (
        <div className="p-12 bg-gradient-to-br from-indigo-50 to-purple-50 h-full">
          <h2 className="text-5xl font-bold mb-8 text-indigo-800">6-Step Workflow</h2>
          
          <div className="grid grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="bg-white rounded-lg p-4 shadow">
                <div className="flex items-center space-x-3">
                  <div className="bg-indigo-600 text-white rounded-full w-8 h-8 flex items-center justify-center font-bold">1</div>
                  <div>
                    <div className="font-semibold">Operator receives inquiry</div>
                    <div className="text-sm text-gray-600">Customer asks in Russian</div>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg p-4 shadow">
                <div className="flex items-center space-x-3">
                  <div className="bg-indigo-600 text-white rounded-full w-8 h-8 flex items-center justify-center font-bold">2</div>
                  <div>
                    <div className="font-semibold">AI Classification</div>
                    <div className="text-sm text-gray-600">Category & subcategory detected</div>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg p-4 shadow">
                <div className="flex items-center space-x-3">
                  <div className="bg-indigo-600 text-white rounded-full w-8 h-8 flex items-center justify-center font-bold">3</div>
                  <div>
                    <div className="font-semibold">Template Retrieval</div>
                    <div className="text-sm text-gray-600">Top 3 relevant templates found</div>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="bg-white rounded-lg p-4 shadow">
                <div className="flex items-center space-x-3">
                  <div className="bg-purple-600 text-white rounded-full w-8 h-8 flex items-center justify-center font-bold">4</div>
                  <div>
                    <div className="font-semibold">Confidence Scoring</div>
                    <div className="text-sm text-gray-600">95% classification confidence</div>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg p-4 shadow">
                <div className="flex items-center space-x-3">
                  <div className="bg-purple-600 text-white rounded-full w-8 h-8 flex items-center justify-center font-bold">5</div>
                  <div>
                    <div className="font-semibold">Template Expansion</div>
                    <div className="text-sm text-gray-600">View full answer text</div>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg p-4 shadow">
                <div className="flex items-center space-x-3">
                  <div className="bg-purple-600 text-white rounded-full w-8 h-8 flex items-center justify-center font-bold">6</div>
                  <div>
                    <div className="font-semibold">Copy & Send</div>
                    <div className="text-sm text-gray-600">One-click to clipboard</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div className="mt-8 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg p-6 text-center">
            <Play className="w-12 h-12 mx-auto mb-3" />
            <div className="text-2xl font-bold">Watch Live Demo Video</div>
            <div className="text-sm mt-2">docs/minsk_hackaton.mp4</div>
          </div>
        </div>
      )
    },
    
    // Slide 6: Technical Highlights
    {
      title: "Technical Highlights",
      content: (
        <div className="p-12 bg-gradient-to-br from-gray-900 to-gray-800 text-white h-full">
          <h2 className="text-5xl font-bold mb-12">Under the Hood</h2>
          
          <div className="grid grid-cols-2 gap-8">
            <div>
              <h3 className="text-2xl font-bold mb-6 text-blue-400">Core Technologies</h3>
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <Code className="w-6 h-6 text-green-400" />
                  <span>Scibox LLM API (OpenAI-compatible)</span>
                </div>
                <div className="flex items-center space-x-3">
                  <Database className="w-6 h-6 text-green-400" />
                  <span>201 pre-vectorized FAQ templates</span>
                </div>
                <div className="flex items-center space-x-3">
                  <Layers className="w-6 h-6 text-green-400" />
                  <span>Docker Compose deployment</span>
                </div>
                <div className="flex items-center space-x-3">
                  <Zap className="w-6 h-6 text-green-400" />
                  <span>FastAPI + React + Nginx stack</span>
                </div>
              </div>
            </div>
            
            <div>
              <h3 className="text-2xl font-bold mb-6 text-purple-400">Smart Features</h3>
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <CheckCircle className="w-6 h-6 text-yellow-400" />
                  <span>Input sanitization & validation</span>
                </div>
                <div className="flex items-center space-x-3">
                  <CheckCircle className="w-6 h-6 text-yellow-400" />
                  <span>Exponential backoff retry logic</span>
                </div>
                <div className="flex items-center space-x-3">
                  <CheckCircle className="w-6 h-6 text-yellow-400" />
                  <span>Performance tracking & metrics</span>
                </div>
                <div className="flex items-center space-x-3">
                  <CheckCircle className="w-6 h-6 text-yellow-400" />
                  <span>Health checks & monitoring</span>
                </div>
              </div>
            </div>
          </div>
          
          <div className="mt-12 bg-gray-700 rounded-lg p-6">
            <h3 className="text-xl font-bold mb-4 text-cyan-400">Knowledge Base Coverage</h3>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div className="bg-gray-800 rounded p-3">
                <div className="text-2xl font-bold text-green-400">6</div>
                <div className="text-gray-400">Main Categories</div>
              </div>
              <div className="bg-gray-800 rounded p-3">
                <div className="text-2xl font-bold text-blue-400">35</div>
                <div className="text-gray-400">Subcategories</div>
              </div>
              <div className="bg-gray-800 rounded p-3">
                <div className="text-2xl font-bold text-purple-400">201</div>
                <div className="text-gray-400">FAQ Templates</div>
              </div>
            </div>
          </div>
        </div>
      )
    },
    
    // Slide 7: Results & Metrics
    {
      title: "Results & Metrics",
      content: (
        <div className="p-12 bg-gradient-to-br from-green-50 to-emerald-50 h-full">
          <h2 className="text-5xl font-bold mb-12 text-green-800">Performance Metrics</h2>
          
          <div className="grid grid-cols-2 gap-8">
            <div className="space-y-6">
              <div className="bg-white rounded-lg shadow-lg p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-gray-600">Classification Accuracy</div>
                    <div className="text-3xl font-bold text-green-600">95%</div>
                  </div>
                  <CheckCircle className="w-12 h-12 text-green-500" />
                </div>
                <div className="text-sm text-gray-500 mt-2">Requirement: &gt;70% ✅</div>
              </div>
              
              <div className="bg-white rounded-lg shadow-lg p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-gray-600">Classification Time</div>
                    <div className="text-3xl font-bold text-blue-600">2.7s</div>
                  </div>
                  <CheckCircle className="w-12 h-12 text-green-500" />
                </div>
                <div className="text-sm text-gray-500 mt-2">Requirement: &lt;3s ✅</div>
              </div>
            </div>
            
            <div className="space-y-6">
              <div className="bg-white rounded-lg shadow-lg p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-gray-600">Retrieval Time</div>
                    <div className="text-3xl font-bold text-purple-600">0.6s</div>
                  </div>
                  <CheckCircle className="w-12 h-12 text-green-500" />
                </div>
                <div className="text-sm text-gray-500 mt-2">Requirement: &lt;1s ✅</div>
              </div>
              
              <div className="bg-white rounded-lg shadow-lg p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-gray-600">Total Response</div>
                    <div className="text-3xl font-bold text-emerald-600">3.3s</div>
                  </div>
                  <CheckCircle className="w-12 h-12 text-green-500" />
                </div>
                <div className="text-sm text-gray-500 mt-2">Requirement: &lt;4s ✅</div>
              </div>
            </div>
          </div>
          
          <div className="mt-8 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg p-6 text-center">
            <Award className="w-16 h-16 mx-auto mb-4" />
            <div className="text-3xl font-bold">All 3 Hackathon Checkpoints</div>
            <div className="text-xl mt-2">✅ Successfully Completed</div>
          </div>
        </div>
      )
    },
    
    // Slide 8: Business Impact
    {
      title: "Business Impact",
      content: (
        <div className="p-12 bg-gradient-to-br from-blue-50 to-indigo-50 h-full">
          <h2 className="text-5xl font-bold mb-12 text-blue-800">Transform Your Support</h2>
          
          <div className="grid grid-cols-2 gap-8">
            <div className="bg-white rounded-lg shadow-lg p-8">
              <TrendingUp className="w-16 h-16 text-green-600 mb-4" />
              <h3 className="text-2xl font-bold mb-4">90%+ Time Savings</h3>
              <p className="text-gray-700">From 5-10 minutes to 3.3 seconds per inquiry</p>
              <div className="mt-6 text-4xl font-bold text-green-600">95x Faster</div>
            </div>
            
            <div className="bg-white rounded-lg shadow-lg p-8">
              <Users className="w-16 h-16 text-blue-600 mb-4" />
              <h3 className="text-2xl font-bold mb-4">Better Experience</h3>
              <p className="text-gray-700">Consistent, high-quality responses every time</p>
              <div className="mt-6 text-4xl font-bold text-blue-600">100% Quality</div>
            </div>
          </div>
          
          <div className="mt-8 space-y-4">
            <div className="bg-gradient-to-r from-purple-100 to-indigo-100 rounded-lg p-4 flex items-center justify-between">
              <span className="text-lg font-semibold">Scalable to thousands of templates</span>
              <BarChart className="w-8 h-8 text-purple-600" />
            </div>
            
            <div className="bg-gradient-to-r from-blue-100 to-cyan-100 rounded-lg p-4 flex items-center justify-between">
              <span className="text-lg font-semibold">Reduced operator training time</span>
              <Clock className="w-8 h-8 text-blue-600" />
            </div>
            
            <div className="bg-gradient-to-r from-green-100 to-emerald-100 rounded-lg p-4 flex items-center justify-between">
              <span className="text-lg font-semibold">Improved customer satisfaction</span>
              <Award className="w-8 h-8 text-green-600" />
            </div>
          </div>
        </div>
      )
    },
    
    // Slide 9: Technical Stack
    {
      title: "Technical Stack",
      content: (
        <div className="p-12 bg-gradient-to-br from-slate-900 to-slate-800 text-white h-full">
          <h2 className="text-5xl font-bold mb-12">Production-Ready Stack</h2>
          
          <div className="grid grid-cols-2 gap-8">
            <div>
              <h3 className="text-2xl font-bold mb-6 text-cyan-400">Backend</h3>
              <div className="bg-slate-700 rounded-lg p-6 space-y-3">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                  <span>Python 3.12</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                  <span>FastAPI</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                  <span>OpenAI Client</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                  <span>SQLite + NumPy</span>
                </div>
              </div>
            </div>
            
            <div>
              <h3 className="text-2xl font-bold mb-6 text-purple-400">Frontend</h3>
              <div className="bg-slate-700 rounded-lg p-6 space-y-3">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-purple-400 rounded-full"></div>
                  <span>React 18</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-purple-400 rounded-full"></div>
                  <span>TypeScript</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-purple-400 rounded-full"></div>
                  <span>Tailwind CSS</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-purple-400 rounded-full"></div>
                  <span>Vite</span>
                </div>
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-8 mt-8">
            <div>
              <h3 className="text-2xl font-bold mb-6 text-yellow-400">AI/ML</h3>
              <div className="bg-slate-700 rounded-lg p-6 space-y-3">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-yellow-400 rounded-full"></div>
                  <span>Qwen2.5-72B (classification)</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-yellow-400 rounded-full"></div>
                  <span>BGE-M3 (embeddings)</span>
                </div>
              </div>
            </div>
            
            <div>
              <h3 className="text-2xl font-bold mb-6 text-red-400">Infrastructure</h3>
              <div className="bg-slate-700 rounded-lg p-6 space-y-3">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-red-400 rounded-full"></div>
                  <span>Docker</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-red-400 rounded-full"></div>
                  <span>Docker Compose</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-red-400 rounded-full"></div>
                  <span>Nginx</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )
    },
    
    // Slide 10: What's Next
    {
      title: "What's Next",
      content: (
        <div className="p-12 bg-gradient-to-br from-purple-50 to-pink-50 h-full">
          <h2 className="text-5xl font-bold mb-12 text-purple-800">Future Enhancements</h2>
          
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-lg p-6 flex items-start space-x-4">
              <div className="bg-purple-600 text-white rounded-full w-10 h-10 flex items-center justify-center font-bold flex-shrink-0">1</div>
              <div>
                <h3 className="text-xl font-bold mb-2">Multi-Language Support</h3>
                <p className="text-gray-700">Russian + English + Belarusian for broader reach</p>
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow-lg p-6 flex items-start space-x-4">
              <div className="bg-purple-600 text-white rounded-full w-10 h-10 flex items-center justify-center font-bold flex-shrink-0">2</div>
              <div>
                <h3 className="text-xl font-bold mb-2">Learning from Feedback</h3>
                <p className="text-gray-700">Improve rankings based on operator choices</p>
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow-lg p-6 flex items-start space-x-4">
              <div className="bg-purple-600 text-white rounded-full w-10 h-10 flex items-center justify-center font-bold flex-shrink-0">3</div>
              <div>
                <h3 className="text-xl font-bold mb-2">System Integration</h3>
                <p className="text-gray-700">Connect with Zendesk, Jira, and other ticketing systems</p>
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow-lg p-6 flex items-start space-x-4">
              <div className="bg-purple-600 text-white rounded-full w-10 h-10 flex items-center justify-center font-bold flex-shrink-0">4</div>
              <div>
                <h3 className="text-xl font-bold mb-2">Analytics Dashboard</h3>
                <p className="text-gray-700">Track support metrics and operator performance</p>
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow-lg p-6 flex items-start space-x-4">
              <div className="bg-purple-600 text-white rounded-full w-10 h-10 flex items-center justify-center font-bold flex-shrink-0">5</div>
              <div>
                <h3 className="text-xl font-bold mb-2">Mobile Interface</h3>
                <p className="text-gray-700">Support operators on-the-go with mobile app</p>
              </div>
            </div>
          </div>
        </div>
      )
    },
    
    // Slide 11: Thank You / Demo
    {
      title: "Thank You",
      content: (
        <div className="flex flex-col items-center justify-center h-full bg-gradient-to-br from-blue-600 via-purple-600 to-green-600 text-white p-12">
          <div className="text-7xl font-bold mb-8">Thank You!</div>
          
          <div className="text-3xl mb-12">Ready for Production Deployment</div>
          
          <div className="space-y-6">
            <div className="flex items-center space-x-4 justify-center">
              <Github className="w-8 h-8" />
              <span className="text-xl">github.com/pandarun/smart-support</span>
            </div>
            
            <div className="flex items-center space-x-4 justify-center">
              <Play className="w-8 h-8" />
              <span className="text-xl">Live Demo Available</span>
            </div>
            
            <div className="flex items-center space-x-4 justify-center">
              <Award className="w-8 h-8" />
              <span className="text-xl">Minsk Hackathon 2025</span>
            </div>
          </div>
          
          <div className="mt-16 p-6 bg-white/10 rounded-lg backdrop-blur">
            <div className="text-2xl font-bold">Questions?</div>
            <div className="text-lg mt-2">Let's see Smart Support in action!</div>
          </div>
        </div>
      )
    }
  ];

  const nextSlide = () => {
    if (currentSlide < slides.length - 1 && !isAnimating) {
      setIsAnimating(true);
      setTimeout(() => {
        setCurrentSlide(currentSlide + 1);
        setIsAnimating(false);
      }, 300);
    }
  };

  const prevSlide = () => {
    if (currentSlide > 0 && !isAnimating) {
      setIsAnimating(true);
      setTimeout(() => {
        setCurrentSlide(currentSlide - 1);
        setIsAnimating(false);
      }, 300);
    }
  };

  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.key === 'ArrowRight' || e.key === ' ') {
        nextSlide();
      } else if (e.key === 'ArrowLeft') {
        prevSlide();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [currentSlide, isAnimating]);

  return (
    <div className="w-full h-screen bg-gray-900 text-gray-800 overflow-hidden relative">
      {/* Slide Content */}
      <div className="w-full h-full">
        {slides[currentSlide].content}
      </div>
      
      {/* Navigation */}
      <div className="absolute bottom-8 left-0 right-0 flex items-center justify-center space-x-4">
        <button
          onClick={prevSlide}
          disabled={currentSlide === 0}
          className={`p-3 rounded-full bg-black/20 backdrop-blur transition-all ${
            currentSlide === 0 ? 'opacity-30 cursor-not-allowed' : 'hover:bg-black/30'
          }`}
        >
          <ChevronLeft className="w-6 h-6 text-white" />
        </button>
        
        {/* Slide Indicators */}
        <div className="flex space-x-2">
          {slides.map((_, index) => (
            <div
              key={index}
              className={`w-2 h-2 rounded-full transition-all ${
                index === currentSlide ? 'w-8 bg-white' : 'bg-white/40'
              }`}
            />
          ))}
        </div>
        
        <button
          onClick={nextSlide}
          disabled={currentSlide === slides.length - 1}
          className={`p-3 rounded-full bg-black/20 backdrop-blur transition-all ${
            currentSlide === slides.length - 1 ? 'opacity-30 cursor-not-allowed' : 'hover:bg-black/30'
          }`}
        >
          <ChevronRight className="w-6 h-6 text-white" />
        </button>
      </div>
      
      {/* Slide Counter */}
      <div className="absolute top-8 right-8 text-white/60 text-sm">
        {currentSlide + 1} / {slides.length}
      </div>
      
      {/* Keyboard Hint */}
      <div className="absolute top-8 left-8 text-white/60 text-sm">
        Use ← → or Space to navigate
      </div>
    </div>
  );
};

export default Presentation;