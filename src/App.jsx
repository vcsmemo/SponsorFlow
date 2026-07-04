import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  Search, 
  UserCheck, 
  Radio, 
  Mail, 
  Video, 
  Sparkles, 
  Layers, 
  DollarSign, 
  Calendar, 
  Tag, 
  CheckCircle,
  X,
  ExternalLink,
  ChevronRight,
  TrendingDown,
  Info,
  RefreshCw,
  Loader2,
  Play,
  ArrowRight,
  Filter,
  Globe,
  Users,
  Award,
  Zap,
  BarChart3,
  Link2,
  Network
} from 'lucide-react';


const SafeImage = ({ src, alt, className, fallbackText }) => {
  const [error, setError] = React.useState(false);
  React.useEffect(() => { setError(false); }, [src]);
  
  if (error || !src) {
    let initial = '?';
    if (fallbackText && typeof fallbackText === 'string') {
        initial = fallbackText.charAt(0).toUpperCase();
    } else if (alt && typeof alt === 'string') {
        initial = alt.charAt(0).toUpperCase();
    }
    return (
      <div className={`${className} flex items-center justify-center font-bold text-slate-400 bg-slate-50`} style={{ padding: 0 }}>
        {initial}
      </div>
    );
  }
  return <img src={src} alt={alt} className={className} onError={() => setError(true)} />;
};

export default function App() {

  // Navigation Router
  const [currentView, setCurrentView] = useState({ page: 'home', params: {} });
  
  // Data State
  const [loading, setLoading] = useState(true);
  const [isScraping, setIsScraping] = useState(false);
  const [scrapeMessage, setScrapeMessage] = useState('');
  
  // Tab-specific datasets
  const [homeData, setHomeData] = useState({
    metrics: { brands_count: 0, brands_delta: '+0', creators_count: 0, creators_delta: '+0' },
    industry_trends: [],
    trending_brands: [],
    trending_creators: [],
    latest_deals: []
  });
  const [allSponsors, setAllSponsors] = useState([]);
  const [allChannels, setAllChannels] = useState([]);
  const [allDeals, setAllDeals] = useState([]);
  const [insights, setInsights] = useState([]);
  const [networkData, setNetworkData] = useState({ nodes: [], links: [] });
  
  // Details datasets
  const [brandDetail, setBrandDetail] = useState(null);
  const [creatorDetail, setCreatorDetail] = useState(null);
  const [dealDetail, setDealDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Search/Filter values
  const [searchText, setSearchText] = useState('');
  const [searchTab, setSearchTab] = useState('brands'); // 'brands' | 'creators'
  const [filterIndustry, setFilterIndustry] = useState('All');
  const [filterPlatform, setFilterPlatform] = useState('All');
  const [filterCountry, setFilterCountry] = useState('All');
  const [filterFollowers, setFilterFollowers] = useState('All');

  // Network force-directed states
  const [nodesState, setNodesState] = useState([]);
  const [linksState, setLinksState] = useState([]);
  const [hoveredNode, setHoveredNode] = useState(null);
  
  // Fetch initial data based on page view
  const fetchHomeData = async () => {
    try {
      const res = await fetch('/api/money-flow');
      if (res.ok) {
        const data = await res.json();
        setHomeData(data);
      }
    } catch (e) { console.error("Error fetching home data:", e); }
  };

  const fetchGlobalLists = async () => {
    try {
      const res = await fetch('/api/dashboard');
      if (res.ok) {
        const data = await res.json();
        setAllSponsors(data.trendingSponsors || []);
        setAllChannels(data.channels || []);
      }
      const res2 = await fetch('/api/signals');
      if (res2.ok) {
        const data2 = await res2.json();
        setAllDeals(data2 || []);
      }
    } catch (e) { console.error("Error listing db:", e); }
  };

  const fetchInsightsData = async () => {
    try {
      const res = await fetch('/api/insights');
      if (res.ok) {
        const data = await res.json();
        setInsights(data);
      }
    } catch (e) { console.error("Error fetching insights:", e); }
  };

  const fetchNetworkMap = async () => {
    try {
      const res = await fetch('/api/network-map');
      if (res.ok) {
        const data = await res.json();
        setNetworkData(data);
      }
    } catch (e) { console.error("Error fetching network:", e); }
  };

  // Details loader
  const loadBrandDetail = async (id) => {
    setDetailLoading(true);
    try {
      const res = await fetch(`/api/sponsors/${id}`);
      if (res.ok) {
        const data = await res.json();
        setBrandDetail(data);
      }
    } catch (e) { console.error(e); }
    setDetailLoading(false);
  };

  const loadCreatorDetail = async (id) => {
    setDetailLoading(true);
    try {
      const res = await fetch(`/api/channels/${id}/earnings`);
      if (res.ok) {
        const data = await res.json();
        setCreatorDetail(data);
      }
    } catch (e) { console.error(e); }
    setDetailLoading(false);
  };

  const loadDealDetail = async (id) => {
    setDetailLoading(true);
    try {
      const res = await fetch(`/api/deals/${id}`);
      if (res.ok) {
        const data = await res.json();
        setDealDetail(data);
      }
    } catch (e) { console.error(e); }
    setDetailLoading(false);
  };

  // Initial load
  useEffect(() => {
    const loadAll = async () => {
      setLoading(true);
      await fetchHomeData();
      await fetchGlobalLists();
      await fetchInsightsData();
      await fetchNetworkMap();
      setLoading(false);
    };
    loadAll();
  }, []);

  // Fetch page dependencies on navigation
  useEffect(() => {
    if (currentView.page === 'brand-detail') {
      loadBrandDetail(currentView.params.id);
    } else if (currentView.page === 'creator-detail') {
      loadCreatorDetail(currentView.params.id);
    } else if (currentView.page === 'deal-detail') {
      loadDealDetail(currentView.params.id);
    }
  }, [currentView]);

  // Network force simulation logic (SVG node positions calculation)
  useEffect(() => {
    if (currentView.page !== 'money-map' || !networkData.nodes.length) return;
    
    let simNodes = networkData.nodes.map((n, i) => {
      const angle = (i / networkData.nodes.length) * 2 * Math.PI;
      const radius = 180 + Math.random() * 40;
      return {
        ...n,
        x: 400 + radius * Math.cos(angle),
        y: 280 + radius * Math.sin(angle),
        vx: 0,
        vy: 0
      };
    });
    
    let simLinks = networkData.links.map(l => ({ ...l }));
    const k = 0.08;
    const repForce = 900;
    let active = true;
    
    const step = () => {
      if (!active) return;
      
      // Repulsive
      for (let i = 0; i < simNodes.length; i++) {
        let n1 = simNodes[i];
        for (let j = i + 1; j < simNodes.length; j++) {
          let n2 = simNodes[j];
          let dx = n2.x - n1.x;
          let dy = n2.y - n1.y;
          if (dx === 0) dx = 0.1;
          let distSq = dx * dx + dy * dy;
          let dist = Math.sqrt(distSq);
          
          if (dist < 350) {
            let force = repForce / (distSq + 20);
            let fx = (dx / dist) * force;
            let fy = (dy / dist) * force;
            
            n1.vx -= fx;
            n1.vy -= fy;
            n2.vx += fx;
            n2.vy += fy;
          }
        }
      }
      
      // Attractive
      simLinks.forEach(l => {
        let nSrc = simNodes.find(n => n.id === l.source);
        let nTgt = simNodes.find(n => n.id === l.target);
        if (nSrc && nTgt) {
          let dx = nTgt.x - nSrc.x;
          let dy = nTgt.y - nSrc.y;
          let dist = Math.sqrt(dx * dx + dy * dy) || 0.1;
          let force = k * (dist - 120);
          let fx = (dx / dist) * force;
          let fy = (dy / dist) * force;
          
          nSrc.vx += fx;
          nSrc.vy += fy;
          nTgt.vx -= fx;
          nTgt.vy -= fy;
        }
      });
      
      // Center & update
      simNodes.forEach(n => {
        n.vx *= 0.82;
        n.vy *= 0.82;
        
        let cx = 400 - n.x;
        let cy = 280 - n.y;
        n.vx += cx * 0.008;
        n.vy += cy * 0.008;
        
        n.x += n.vx;
        n.y += n.vy;
        
        n.x = Math.max(30, Math.min(770, n.x));
        n.y = Math.max(30, Math.min(530, n.y));
      });
      
      setNodesState([...simNodes]);
      setLinksState([...simLinks]);
      requestAnimationFrame(step);
    };
    
    requestAnimationFrame(step);
    return () => { active = false; };
  }, [currentView.page, networkData]);

  // Scraper Trigger
  const handleTriggerScrape = async () => {
    setIsScraping(true);
    setScrapeMessage('Crawling recent feeds...');
    try {
      const res = await fetch('/api/trigger-scrape', { method: 'POST' });
      if (res.ok) {
        const d = await res.json();
        setScrapeMessage(`Ingested ${d.new_signals_detected} sponsorship deals.`);
        await fetchHomeData();
        await fetchGlobalLists();
        await fetchInsightsData();
        await fetchNetworkMap();
      } else {
        setScrapeMessage('Scraper error.');
      }
    } catch (e) {
      setScrapeMessage('Connection error.');
    }
    setTimeout(() => { setIsScraping(false); setScrapeMessage(''); }, 3500);
  };

  // Helper formatting
  const formatFollowersCount = (count) => {
    if (!count || count === 0) return 'N/A';
    if (count >= 1000000) return (count / 1000000).toFixed(1) + 'M';
    if (count >= 1000) return (count / 1000).toFixed(0) + 'K';
    return count;
  };

  const getPlatformIcon = (platform) => {
    switch(platform) {
      case 'youtube': return <Video className="w-4 h-4 text-rose-600" />;
      case 'podcast': return <Radio className="w-4 h-4 text-[#876e5f]" />;
      case 'newsletter': return <Mail className="w-4 h-4 text-emerald-700" />;
      default: return null;
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen text-slate-800 bg-[#fbf9f6]">
        <Loader2 className="w-10 h-10 animate-spin text-[#e27b58] mb-4" />
        <span className="text-sm font-semibold tracking-wider text-slate-500 uppercase">Loading budget signal flows...</span>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen text-slate-800 bg-[#fbf9f6] selection:bg-[#e27b58]/10 selection:text-[#876e5f]">
      {/* Sidebar Navigation */}
      <aside className="w-64 shrink-0 border-r border-[#e8e2d9] bg-white flex flex-col justify-between p-4 sticky top-0 h-screen shadow-sm shadow-slate-100">
        <div className="space-y-6">
          {/* Logo */}
          <div className="flex items-center gap-2.5 px-2 py-1">
            <div className="w-8 h-8 rounded-lg bg-[#e27b58] flex items-center justify-center shadow-lg shadow-[#e27b58]/10">
              <Layers className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight text-slate-900 leading-none">SponsorFlow.io</h1>
              <span className="text-[10px] text-slate-400 tracking-wider font-semibold">CREATOR BUDGET RADAR</span>
            </div>
          </div>

          {/* Nav Links */}
          <nav className="space-y-1.5">
            {[
              { id: 'home', label: 'Home', icon: Layers },
              { id: 'brands', label: 'Brands', icon: Award },
              { id: 'creators', label: 'Creators', icon: Users },
              { id: 'deals', label: 'Deals', icon: Link2 },
              { id: 'rankings', label: 'Rankings', icon: BarChart3 },
              { id: 'categories', label: 'Categories', icon: Tag },
              { id: 'insights', label: 'Insights', icon: Sparkles },
              { id: 'search', label: 'Search', icon: Search },
              { id: 'money-map', label: 'Money Map', icon: Network }
            ].map(tab => {
              const IconComp = tab.icon;
              const isActive = currentView.page === tab.id || currentView.page.startsWith(tab.id + '-');
              return (
                <button
                  key={tab.id}
                  onClick={() => setCurrentView({ page: tab.id, params: {} })}
                  className={`w-full flex items-center gap-3 px-3.5 py-2.5 text-sm font-semibold rounded transition-all ${
                    isActive 
                      ? 'bg-[#f5f2eb] text-[#876e5f] border-l-2 border-[#876e5f] font-bold shadow-sm' 
                      : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50 border-l-2 border-transparent'
                  }`}
                >
                  <IconComp className="w-5 h-5" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Action Bottom */}
        <div className="border-t border-slate-100 pt-4 space-y-3">
          {scrapeMessage && (
            <div className="px-3 py-2 rounded bg-slate-50 border border-[#e8e2d9] text-xs text-slate-500 flex items-center gap-1.5 animate-pulse">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-[#e27b58]" />
              <span>{scrapeMessage}</span>
            </div>
          )}
          <button
            onClick={handleTriggerScrape}
            disabled={isScraping}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 bg-[#e27b58] hover:bg-[#d66f4c] disabled:bg-slate-50 disabled:text-slate-400 text-xs font-bold text-white rounded transition-all shadow shadow-[#e27b58]/10"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isScraping ? 'animate-spin' : ''}`} />
            Trigger Live Radar Scrape
          </button>
          <div className="text-center pt-1">
            <span className="text-[10px] text-slate-400 font-semibold">SponsorFlow Terminal v1.2</span>
          </div>
        </div>
      </aside>

      {/* Main Panel Content */}
      <main className="flex-1 bg-[#fbf9f6] overflow-y-auto">
        <header className="border-b border-[#e8e2d9] bg-white/70 px-6 py-4.5 flex items-center justify-between sticky top-0 backdrop-blur-md z-30 shadow-sm shadow-slate-100/30">
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase font-bold tracking-wider text-[#876e5f] bg-[#f5f2eb] px-2 py-0.5 rounded">Terminal Feed</span>
            <span className="text-slate-300">/</span>
            <span className="text-sm font-semibold text-slate-500">
              {currentView.page === 'home' && 'Yesterday\'s Money Flow'}
              {currentView.page === 'brands' && 'Brand Sponsors Database'}
              {currentView.page === 'creators' && 'Creator Profiles'}
              {currentView.page === 'deals' && 'Ad Placements Catalog'}
              {currentView.page === 'rankings' && 'Leaderboard Rankings'}
              {currentView.page === 'categories' && 'Marketing Niches Catalog'}
              {currentView.page === 'insights' && 'AI Market Trends Insights'}
              {currentView.page === 'search' && 'Advanced Crunchbase Filtering'}
              {currentView.page === 'money-map' && 'Money Map Topology Graph'}
              {currentView.page.endsWith('-detail') && 'Detailed Profile View'}
            </span>
          </div>
          <div className="text-sm text-slate-550 flex items-center gap-1.5 font-medium">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></div>
            <span className="font-semibold text-slate-600">Live Ingesting</span>
          </div>
        </header>

        <div className="p-6 max-w-6xl mx-auto space-y-6">
          {/* ======================================================== */}
          {/* PAGE: HOME (Money Flow Dashboard)                        */}
          {/* ======================================================== */}
          {currentView.page === 'home' && (
            <div className="space-y-6">
              {/* Product Intro Positioning */}
              <div className="border border-[#e8e2d9] bg-white rounded-xl p-6 relative overflow-hidden shadow-sm">
                <div className="absolute right-0 bottom-0 opacity-[0.02] translate-x-12 translate-y-12 select-none pointer-events-none">
                  <Layers className="w-72 h-72 text-slate-900" />
                </div>
                <h2 className="text-2xl md:text-3xl font-black tracking-tight text-[#191919] mb-2 font-serif-title">Where marketing dollars go.</h2>
                <p className="text-sm md:text-base text-slate-600 leading-relaxed max-w-2xl">
                  Track where brands spend money on creators. Real-time sponsorship intelligence across podcasts, newsletters, and YouTube channels.
                </p>
              </div>

              {/* Money Flow Yesterday Dashboard Card */}
              <div className="glass-panel rounded-xl p-5 shadow-sm">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3.5 mb-4">
                  <span className="text-xs font-black tracking-widest text-slate-500 uppercase">💰 MARKETING MONEY FLOW</span>
                  <span className="text-xs font-bold text-[#876e5f] bg-[#f5f2eb] px-2.5 py-0.5 rounded">Yesterday</span>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
                  {/* Metric Block 1 */}
                  <div className="space-y-1">
                    <span className="text-xs text-slate-400 uppercase block font-semibold">Brands Sponsoring</span>
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-black text-slate-900 font-serif-title">{homeData.metrics.brands_count}</span>
                      <span className="text-xs font-black text-emerald-600">{homeData.metrics.brands_delta}</span>
                    </div>
                  </div>
                  {/* Metric Block 2 */}
                  <div className="space-y-1">
                    <span className="text-xs text-slate-400 uppercase block font-semibold">New Partnerships</span>
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-black text-slate-900 font-serif-title">{homeData.metrics.creators_count}</span>
                      <span className="text-xs font-black text-emerald-600">{homeData.metrics.creators_delta}</span>
                    </div>
                  </div>
                  {/* Industry trends */}
                  {homeData.industry_trends.slice(0, 3).map((ind, idx) => (
                    <div key={idx} className="space-y-1">
                      <span className="text-xs text-slate-400 uppercase block font-semibold">{ind.name}</span>
                      <div className="flex items-baseline gap-2">
                        <span className="text-xl font-black text-slate-800 font-serif-title">{ind.change}</span>
                        <span className={`text-xs font-black ${ind.direction === 'up' ? 'text-emerald-600' : 'text-rose-600'}`}>
                          {ind.direction === 'up' ? '↑' : '↓'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Trending Brands */}
                <div className="glass-panel rounded-xl p-5 shadow-sm">
                  <h3 className="text-xs font-black tracking-widest text-slate-550 uppercase border-b border-slate-100 pb-3 mb-3">TRENDING BRANDS</h3>
                  <div className="divide-y divide-slate-100">
                    {homeData.trending_brands.map((sp, idx) => (
                      <div 
                        key={idx} 
                        onClick={() => setCurrentView({ page: 'brand-detail', params: { id: sp.id } })}
                        className="flex items-center justify-between py-3 hover:bg-slate-50 px-2 rounded cursor-pointer transition-all"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-bold text-slate-400 w-4">#{idx+1}</span>
                          {sp.logo_url ? (
                            <SafeImage src={sp.logo_url} className="w-5 h-5 rounded object-contain border border-slate-100 bg-white" alt={sp.name} fallbackText={sp.name} />
                          ) : (
                            <div className="w-5 h-5 rounded bg-[#f5f2eb] text-[9px] font-bold text-[#876e5f] flex items-center justify-center border border-[#e8e2d9]">{sp.name[0]}</div>
                          )}
                          <span className="text-sm font-bold text-slate-700 hover:text-[#e27b58] transition-colors">{sp.name}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-slate-400 font-semibold">{sp.industry}</span>
                          <span className="text-xs font-bold text-emerald-650 flex items-center gap-0.5">
                            <TrendingUp className="w-3.5 h-3.5" />
                            {sp.delta}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Trending Creators */}
                <div className="glass-panel rounded-xl p-5 shadow-sm">
                  <h3 className="text-xs font-black tracking-widest text-slate-550 uppercase border-b border-slate-100 pb-3 mb-3">TRENDING CREATORS</h3>
                  <div className="divide-y divide-slate-100">
                    {homeData.trending_creators.map((ch, idx) => (
                      <div 
                        key={idx} 
                        onClick={() => setCurrentView({ page: 'creator-detail', params: { id: ch.id } })}
                        className="flex items-center justify-between py-3 hover:bg-slate-50 px-2 rounded cursor-pointer transition-all"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-bold text-slate-400 w-4">#{idx+1}</span>
                          {ch.avatar_url ? (
                            <SafeImage src={ch.avatar_url} className="w-5 h-5 rounded-full object-cover border border-slate-100 bg-white" alt={ch.name} fallbackText={ch.name} />
                          ) : (
                            <div className="w-5 h-5 rounded-full bg-slate-100 text-[9px] font-bold text-slate-500 flex items-center justify-center">{ch.name[0]}</div>
                          )}
                          <span className="text-sm font-bold text-slate-700 hover:text-[#e27b58] transition-colors">{ch.name}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-slate-400 font-semibold">{formatFollowersCount(ch.followers)} followers</span>
                          <span className="text-xs font-bold text-[#876e5f] flex items-center gap-0.5">
                            {getPlatformIcon(ch.platform)}
                            {ch.delta}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Latest Deals */}
              <div className="glass-panel rounded-xl p-5 shadow-sm">
                <h3 className="text-xs font-black tracking-widest text-slate-555 uppercase border-b border-slate-100 pb-3 mb-3">LATEST DEALS DETECTED</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="text-slate-400 border-b border-slate-100">
                        <th className="py-3 font-bold uppercase text-[10px]">Sponsor Brand</th>
                        <th className="py-3 font-bold uppercase text-[10px]">Creator</th>
                        <th className="py-3 font-bold uppercase text-[10px]">Platform</th>
                        <th className="py-3 font-bold uppercase text-[10px]">Product Promoted</th>
                        <th className="py-3 font-bold uppercase text-[10px] text-right">Est. Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {homeData.latest_deals.map((deal) => (
                        <tr 
                          key={deal.id} 
                          onClick={() => setCurrentView({ page: 'deal-detail', params: { id: deal.id } })}
                          className="hover:bg-slate-50/80 cursor-pointer group"
                        >
                          <td className="py-3.5">
                            <div className="flex items-center gap-2">
                              {deal.sponsor_logo ? (
                                <SafeImage src={deal.sponsor_logo} className="w-5 h-5 rounded object-contain border border-slate-100 bg-white" alt="" fallbackText={(deal.sponsor_brand_name || deal.channel_name || "?")} />
                              ) : (
                                <div className="w-5 h-5 rounded bg-[#f5f2eb] text-[8px] font-bold text-[#876e5f] flex items-center justify-center border border-[#e8e2d9]">{deal.sponsor_name[0]}</div>
                              )}
                              <span className="font-bold text-slate-700 group-hover:text-[#e27b58] transition-colors">{deal.sponsor_name}</span>
                            </div>
                          </td>
                          <td className="py-3.5">
                            <div className="flex items-center gap-2">
                              {deal.channel_avatar ? (
                                <SafeImage src={deal.channel_avatar} className="w-5 h-5 rounded-full object-cover" alt="" fallbackText={(deal.sponsor_brand_name || deal.channel_name || "?")} />
                              ) : (
                                <div className="w-5 h-5 rounded-full bg-slate-100 text-[8px] font-bold text-slate-500 flex items-center justify-center">{deal.channel_name[0]}</div>
                              )}
                              <span className="font-medium text-slate-700">{deal.channel_name}</span>
                            </div>
                          </td>
                          <td className="py-3.5">
                            <span className="inline-flex items-center gap-1 bg-slate-50 border border-slate-200/50 px-2 py-0.5 rounded text-[11px] text-slate-500 capitalize font-bold">
                              {getPlatformIcon(deal.platform)}
                              {deal.platform}
                            </span>
                          </td>
                          <td className="py-3.5 text-slate-500 font-medium">{deal.product}</td>
                          <td className="py-3.5 text-right font-black text-slate-800">{deal.estimated_value}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* PAGE: BRANDS (Sponsors Database)                        */}
          {/* ======================================================== */}
          {currentView.page === 'brands' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-black text-slate-900 font-serif-title">Sponsor Brands</h2>
                <p className="text-sm text-slate-500 font-medium mt-1">Database of companies actively purchasing developer and creator sponsorships.</p>
              </div>

              {/* Brands Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {allSponsors.map((sp) => (
                  <div 
                    key={sp.id}
                    onClick={() => setCurrentView({ page: 'brand-detail', params: { id: sp.id } })}
                    className="glass-panel border border-[#e8e2d9] hover:border-[#e27b58]/55 rounded p-5 cursor-pointer transition-all group flex items-start justify-between shadow-sm"
                  >
                    <div className="space-y-3">
                      <div className="flex items-center gap-3">
                        {sp.logo_url ? (
                          <SafeImage src={sp.logo_url} className="w-7 h-7 rounded object-contain border border-slate-100 bg-white p-0.5" alt="" fallbackText={sp.brand_name || sp.name || "?"} />
                        ) : (
                          <div className="w-7 h-7 rounded bg-[#f5f2eb] text-xs font-bold text-[#876e5f] flex items-center justify-center border border-[#e8e2d9]">{sp.name[0]}</div>
                        )}
                        <h3 className="text-sm font-black text-slate-800 group-hover:text-[#e27b58] transition-colors">{sp.name}</h3>
                      </div>
                      <div className="flex gap-2">
                        <span className="text-[10px] bg-slate-50 text-slate-500 font-bold px-2 py-0.5 rounded border border-[#e8e2d9]/60">{sp.industry}</span>
                        {sp.isAiStartup && (
                          <span className="text-[10px] bg-[#f5f2eb] text-[#876e5f] font-bold px-2 py-0.5 rounded border border-[#e8e2d9]">AI Native</span>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] text-slate-400 uppercase block font-semibold">Total Allocation</span>
                      <span className="text-sm font-black text-slate-800 font-serif-title">{sp.estimatedSpend}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* DETAIL VIEW: BRAND PROFILE                               */}
          {/* ======================================================== */}
          {currentView.page === 'brand-detail' && (
            <div className="space-y-6">
              {detailLoading ? (
                <div className="flex items-center justify-center py-20 text-slate-400">
                  <Loader2 className="w-6 h-6 animate-spin text-[#e27b58] mr-2" /> Loading brand profile...
                </div>
              ) : brandDetail && (
                <>
                  <button 
                    onClick={() => setCurrentView({ page: 'brands', params: {} })}
                    className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-850 font-bold transition-all"
                  >
                    ← Back to Sponsors
                  </button>

                  {/* Brand Profile Hero Block */}
                  <div className="glass-panel border border-[#e8e2d9] rounded p-6 relative overflow-hidden flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-sm">
                    <div className="flex items-center gap-4">
                      {brandDetail.sponsor.logo_url ? (
                        <SafeImage src={brandDetail.sponsor.logo_url} className="w-14 h-14 rounded object-contain border border-[#e8e2d9] bg-white p-1" alt="" fallbackText={brandDetail.sponsor.brand_name || "?"} />
                      ) : (
                        <div className="w-14 h-14 rounded bg-[#f5f2eb] text-2xl font-bold text-[#876e5f] flex items-center justify-center border border-[#e8e2d9]">{brandDetail.sponsor.brand_name[0]}</div>
                      )}
                      <div>
                        <h2 className="text-2xl font-black text-slate-900 font-serif-title">{brandDetail.sponsor.brand_name}</h2>
                        <span className="inline-block text-[10px] bg-slate-50 text-slate-500 font-bold px-2.5 py-0.5 rounded border border-[#e8e2d9] mt-1.5">{brandDetail.sponsor.industry_tag}</span>
                      </div>
                    </div>
                    
                    <div className="flex gap-8 items-center bg-slate-50/50 border border-[#e8e2d9] p-4 rounded">
                      <div className="text-center md:text-left">
                        <span className="text-[10px] text-slate-450 uppercase block font-semibold">Creator Count</span>
                        <span className="text-lg font-black text-slate-800 font-serif-title">{brandDetail.creator_count}</span>
                      </div>
                      <div className="text-center md:text-left">
                        <span className="text-[10px] text-slate-450 uppercase block font-semibold">Sponsored Placements</span>
                        <span className="text-lg font-black text-slate-800 font-serif-title">{brandDetail.total_placements}</span>
                      </div>
                      <div className="text-center md:text-left">
                        <span className="text-[10px] text-slate-450 uppercase block font-semibold">Total Spend Est.</span>
                        <span className="text-lg font-black text-[#e27b58] font-serif-title">{brandDetail.total_estimated_spend}</span>
                      </div>
                    </div>
                  </div>

                  {/* Brand Profile Body Grid */}
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Stats Card */}
                    <div className="lg:col-span-1 space-y-6">
                      <div className="glass-panel border border-[#e8e2d9] rounded p-5 space-y-4 shadow-sm">
                        <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest border-b border-slate-100 pb-2.5">Sponsorship Radar</h3>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase block font-semibold">First Detected</span>
                            <span className="text-xs font-bold text-slate-700">{brandDetail.first_seen}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase block font-semibold">Last Detected</span>
                            <span className="text-xs font-bold text-slate-700">{brandDetail.last_seen}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase block font-semibold">Growth Index</span>
                            <span className="text-xs font-bold text-emerald-600 font-serif-title">{brandDetail.growth}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase block font-semibold">Global Domain</span>
                            <a href={brandDetail.sponsor.global_website} target="_blank" rel="noreferrer" className="text-xs font-bold text-[#e27b58] hover:underline flex items-center gap-1">
                              Visit site <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                          </div>
                        </div>
                      </div>

                      {/* Yearly Timeline (DENSE BARS) */}
                      <div className="glass-panel border border-[#e8e2d9] rounded p-5 shadow-sm">
                        <h3 className="text-xs font-black text-slate-550 uppercase tracking-widest border-b border-slate-100 pb-2.5 mb-3">Yearly Placements Timeline</h3>
                        <div className="space-y-3.5">
                          {brandDetail.timeline.map((item, idx) => {
                            const maxVal = Math.max(...brandDetail.timeline.map(t => t.count)) || 1;
                            const pct = Math.round((item.count / maxVal) * 100);
                            return (
                              <div key={idx} className="space-y-1.5">
                                <div className="flex items-center justify-between text-xs font-bold">
                                  <span className="text-slate-500">{item.year}</span>
                                  <span className="text-slate-700">{item.count} deals</span>
                                </div>
                                <div className="w-full h-3 rounded bg-slate-50 border border-[#e8e2d9]/60 relative overflow-hidden">
                                  <div 
                                    className="h-full bg-[#876e5f] rounded" 
                                    style={{ width: `${pct}%` }}
                                  ></div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* Top Creators list */}
                      <div className="glass-panel border border-[#e8e2d9] rounded p-5 shadow-sm">
                        <h3 className="text-xs font-black text-slate-550 uppercase tracking-widest border-b border-slate-100 pb-2.5 mb-3">Top Creators sponsored</h3>
                        <div className="divide-y divide-slate-100">
                          {brandDetail.top_creators.map((c, idx) => (
                            <div 
                              key={idx}
                              onClick={() => setCurrentView({ page: 'creator-detail', params: { id: c.id } })}
                              className="flex items-center justify-between py-2.5 cursor-pointer hover:bg-slate-50 px-1.5 rounded transition-colors"
                            >
                              <div className="flex items-center gap-2">
                                {c.avatar ? (
                                  <SafeImage src={c.avatar} className="w-5 h-5 rounded-full object-cover border border-[#e8e2d9]/40" alt="" fallbackText={c.name || "?"} />
                                ) : (
                                  <div className="w-5 h-5 rounded-full bg-slate-100 text-[8px] font-bold text-slate-450 flex items-center justify-center">{c.name[0]}</div>
                                )}
                                <span className="text-xs font-bold text-slate-700 hover:text-[#e27b58] transition-colors">{c.name}</span>
                              </div>
                              <span className="text-[10px] text-slate-500 font-bold bg-slate-100 px-1.5 py-0.5 rounded">{c.count} placements</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Recent Sponsorships Placements List */}
                    <div className="lg:col-span-2 glass-panel border border-[#e8e2d9] rounded p-5 shadow-sm">
                      <h3 className="text-xs font-black text-slate-550 uppercase tracking-widest border-b border-slate-100 pb-2.5 mb-4">Sponsorship History</h3>
                      <div className="space-y-4">
                        {brandDetail.placements.map((p, idx) => (
                          <div 
                            key={idx}
                            onClick={() => setCurrentView({ page: 'deal-detail', params: { id: p.id } })}
                            className="border border-[#e8e2d9] bg-white hover:border-[#e27b58]/40 p-5 rounded cursor-pointer transition-all space-y-3.5 shadow-sm"
                          >
                            <div className="flex items-center justify-between text-sm">
                              <div className="flex items-center gap-2.5">
                                {p.channel_avatar ? (
                                  <SafeImage src={p.channel_avatar} className="w-5 h-5 rounded-full object-cover border border-slate-100" alt="" fallbackText={p.channel_name || "?"} />
                                ) : (
                                  <div className="w-5 h-5 rounded-full bg-slate-100 text-[8px] font-bold text-slate-500 flex items-center justify-center">{p.channel_name[0]}</div>
                                )}
                                <span className="font-black text-slate-800">{p.channel_name}</span>
                                <span className="inline-flex items-center gap-1 bg-slate-50 border border-[#e8e2d9] px-2 py-0.5 rounded text-[10px] text-slate-500 font-bold capitalize">
                                  {getPlatformIcon(p.platform)}
                                  {p.platform}
                                </span>
                              </div>
                              <span className="font-black text-[#e27b58] font-serif-title text-base">{p.estimated_value}</span>
                            </div>
                            <p className="text-sm text-slate-650 leading-relaxed bg-[#fbf9f6] p-3 rounded italic border border-[#e8e2d9]/60">"{p.ad_copy}"</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ======================================================== */}
          {/* PAGE: CREATORS (Creators Database)                       */}
          {/* ======================================================== */}
          {currentView.page === 'creators' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-black text-slate-900 font-serif-title">Creator Profiles</h2>
                <p className="text-sm text-slate-400 font-medium mt-1">Niche-specific developer communities, podcasts, and digital newsletters receiving sponsorships.</p>
              </div>

              {/* Creators Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {allChannels.map((ch) => (
                  <div 
                    key={ch.id}
                    onClick={() => setCurrentView({ page: 'creator-detail', params: { id: ch.id } })}
                    className="glass-panel border border-[#e8e2d9] hover:border-[#e27b58]/55 rounded p-5 cursor-pointer transition-all group flex items-start justify-between shadow-sm"
                  >
                    <div className="flex gap-3.5">
                      {ch.avatar_url ? (
                        <SafeImage src={ch.avatar_url} className="w-11 h-11 rounded-full object-cover border border-[#e8e2d9] bg-white shadow-sm" alt="" fallbackText={ch.name || "?"} />
                      ) : (
                        <div className="w-11 h-11 rounded-full bg-[#f5f2eb] text-sm font-bold text-[#876e5f] flex items-center justify-center border border-[#e8e2d9]">{ch.name[0]}</div>
                      )}
                      <div className="space-y-1">
                        <h3 className="text-sm font-black text-slate-700 group-hover:text-[#e27b58] transition-colors">{ch.name}</h3>
                        <div className="flex gap-2.5">
                          <span className="text-[10px] bg-slate-50 border border-[#e8e2d9] text-slate-500 font-bold px-1.5 py-0.5 rounded capitalize inline-flex items-center gap-1">
                            {getPlatformIcon(ch.platform)}
                            {ch.platform}
                          </span>
                          <span className="text-[10px] text-slate-400 font-bold block pt-1">{formatFollowersCount(ch.followers)} followers</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* DETAIL VIEW: CREATOR PROFILE                             */}
          {/* ======================================================== */}
          {currentView.page === 'creator-detail' && (
            <div className="space-y-6">
              {detailLoading ? (
                <div className="flex items-center justify-center py-20 text-slate-400">
                  <Loader2 className="w-6 h-6 animate-spin text-[#e27b58] mr-2" /> Loading creator profile...
                </div>
              ) : creatorDetail && (
                <>
                  <button 
                    onClick={() => setCurrentView({ page: 'creators', params: {} })}
                    className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-850 font-bold transition-all"
                  >
                    ← Back to Creators
                  </button>

                  {/* Creator Profile Hero Block */}
                  <div className="glass-panel border border-[#e8e2d9] rounded p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-sm">
                    <div className="flex items-center gap-4">
                      {creatorDetail.channel.avatar_url ? (
                        <SafeImage src={creatorDetail.channel.avatar_url} className="w-14 h-14 rounded-full object-cover border border-[#e8e2d9] bg-white shadow-sm" alt="" fallbackText={creatorDetail.channel.name || "?"} />
                      ) : (
                        <div className="w-14 h-14 rounded-full bg-[#f5f2eb] text-xl font-bold text-[#876e5f] flex items-center justify-center border border-[#e8e2d9]">{creatorDetail.channel.name[0]}</div>
                      )}
                      <div>
                        <h2 className="text-2xl font-black text-slate-900 font-serif-title">{creatorDetail.channel.name}</h2>
                        <div className="flex items-center gap-2.5 mt-1.5">
                          <span className="inline-flex items-center gap-1 text-[10px] bg-slate-50 border border-[#e8e2d9] text-slate-500 font-bold px-2.5 py-0.5 rounded capitalize">
                            {getPlatformIcon(creatorDetail.channel.platform)}
                            {creatorDetail.channel.platform}
                          </span>
                          <span className="text-xs text-slate-400 font-bold">{formatFollowersCount(creatorDetail.channel.followers)} followers</span>
                          <span className="text-slate-300">•</span>
                          <span className="text-[10px] text-slate-500 font-bold uppercase">{creatorDetail.channel.country || 'US'}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex gap-8 items-center bg-slate-50/50 border border-[#e8e2d9] p-4 rounded">
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase block font-semibold">Active Campaigns</span>
                        <span className="text-lg font-black text-slate-800 font-serif-title">{creatorDetail.placement_count}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase block font-semibold">Per-Ad Estimate</span>
                        <span className="text-lg font-black text-slate-800 font-serif-title">{creatorDetail.per_placement_estimate.display}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase block font-semibold">Total Revenue Est.</span>
                        <span className="text-lg font-black text-emerald-650 font-serif-title">{creatorDetail.total_estimated_earnings}</span>
                      </div>
                    </div>
                  </div>

                  {/* Creator Profile Body Grid */}
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Stats */}
                    <div className="lg:col-span-1 space-y-6">
                      <div className="glass-panel border border-[#e8e2d9] rounded p-5 space-y-4 shadow-sm">
                        <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest border-b border-slate-100 pb-2.5">Sponsorship Profile</h3>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase block font-semibold">Ad Frequency</span>
                            <span className="text-xs font-bold text-slate-700">{creatorDetail.frequency}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase block font-semibold">Niche Index</span>
                            <span className="text-xs font-bold text-slate-700">Tech / Dev</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase block font-semibold">Est. CPM</span>
                            <span className="text-xs font-bold text-[#e27b58] font-serif-title">$30.00</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase block font-semibold">Profile URL</span>
                            <a href={creatorDetail.channel.raw_url} target="_blank" rel="noreferrer" className="text-xs font-bold text-[#e27b58] hover:underline flex items-center gap-1">
                              Source Feed <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                          </div>
                        </div>
                      </div>

                      {/* Brands Worked With */}
                      <div className="glass-panel border border-[#e8e2d9] rounded p-5 shadow-sm">
                        <h3 className="text-xs font-black text-slate-550 uppercase tracking-widest border-b border-slate-100 pb-2.5 mb-3">Brands Worked With</h3>
                        <div className="space-y-3">
                          {creatorDetail.brands_worked_with.map((b, idx) => (
                            <div 
                              key={idx}
                              onClick={() => setCurrentView({ page: 'brand-detail', params: { id: b.id } })}
                              className="flex items-center justify-between cursor-pointer hover:bg-slate-50 p-2 rounded transition-colors"
                            >
                              <div className="flex items-center gap-2.5">
                                {b.logo ? (
                                  <SafeImage src={b.logo} className="w-5 h-5 rounded object-contain border border-slate-100 bg-white" alt="" fallbackText={b.brand_name || b.name || "?"} />
                                ) : (
                                  <div className="w-5 h-5 rounded bg-slate-100 text-[8px] font-bold text-slate-400 flex items-center justify-center">{b.name[0]}</div>
                                )}
                                <span className="text-xs font-bold text-slate-700 hover:text-[#e27b58] transition-colors">{b.name}</span>
                              </div>
                              <span className="text-[10px] text-slate-500 font-bold bg-slate-100 px-2 py-0.5 rounded">{b.count} times</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Industry Distribution */}
                      <div className="glass-panel border border-[#e8e2d9] rounded p-5 shadow-sm">
                        <h3 className="text-xs font-black text-slate-550 uppercase tracking-widest border-b border-slate-100 pb-2.5 mb-3">Industry Distribution</h3>
                        <div className="space-y-3.5">
                          {creatorDetail.industry_distribution.map((ind, idx) => {
                            const maxVal = Math.max(...creatorDetail.industry_distribution.map(i => i.count)) || 1;
                            const pct = Math.round((ind.count / maxVal) * 100);
                            return (
                              <div key={idx} className="space-y-1">
                                <div className="flex items-center justify-between text-xs font-bold">
                                  <span className="text-slate-500">{ind.industry}</span>
                                  <span className="text-slate-700">{ind.count} brands</span>
                                </div>
                                <div className="w-full h-2 rounded bg-slate-100 border border-[#e8e2d9]/60 overflow-hidden">
                                  <div className="h-full bg-emerald-600" style={{ width: `${pct}%` }}></div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>

                    {/* Sponsorship History */}
                    <div className="lg:col-span-2 glass-panel border border-[#e8e2d9] rounded p-5 shadow-sm">
                      <h3 className="text-xs font-black text-slate-550 uppercase tracking-widest border-b border-slate-100 pb-2.5 mb-4">Sponsorship History</h3>
                      <div className="space-y-4">
                        {creatorDetail.history.map((h, idx) => (
                          <div 
                            key={idx}
                            onClick={() => setCurrentView({ page: 'deal-detail', params: { id: h.id } })}
                            className="border border-[#e8e2d9] bg-white hover:border-[#e27b58]/40 p-4.5 rounded cursor-pointer transition-all flex items-center justify-between gap-4 shadow-sm"
                          >
                            <div className="space-y-1.5 flex-1">
                              <div className="flex items-center gap-2.5">
                                {h.sponsor_logo ? (
                                  <SafeImage src={h.sponsor_logo} className="w-5 h-5 rounded object-contain border border-slate-100 bg-white" alt="" fallbackText={h.sponsor_brand_name || "?"} />
                                ) : (
                                  <div className="w-5 h-5 rounded bg-slate-100 text-[8px] font-bold text-slate-500 flex items-center justify-center">{h.sponsor_name[0]}</div>
                                )}
                                <span className="text-xs font-black text-slate-800">{h.sponsor_name}</span>
                              </div>
                              <div className="text-xs text-slate-500 font-semibold">Product: <span className="text-slate-700 font-bold">{h.product}</span></div>
                            </div>
                            <div className="text-right shrink-0">
                              <span className="text-[10px] text-slate-400 uppercase block font-semibold">Confidence</span>
                              <span className="text-xs font-black text-emerald-605">{Math.round(h.confidence * 100)}%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ======================================================== */}
          {/* PAGE: DEALS (Ad Placements Catalog)                     */}
          {/* ======================================================== */}
          {currentView.page === 'deals' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-black text-slate-900 font-serif-title">Ad Placements Catalog</h2>
                <p className="text-sm text-slate-400 font-medium mt-1">Historical archive of sponsorship ad segments detected across digital feeds.</p>
              </div>

              {/* Deals Table */}
              <div className="glass-panel border border-[#e8e2d9] rounded p-5 shadow-sm">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="text-slate-405 border-b border-slate-100">
                        <th className="py-3 font-bold uppercase text-[10px]">Sponsor Brand</th>
                        <th className="py-3 font-bold uppercase text-[10px]">Creator</th>
                        <th className="py-3 font-bold uppercase text-[10px]">Ad Match Content</th>
                        <th className="py-3 font-bold uppercase text-[10px] text-right">Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {allDeals.map((deal) => (
                        <tr 
                          key={deal.id} 
                          onClick={() => setCurrentView({ page: 'deal-detail', params: { id: deal.id } })}
                          className="hover:bg-slate-50 cursor-pointer group animate-fade-in"
                        >
                          <td className="py-3.5">
                            <div className="flex items-center gap-2">
                              {deal.sponsor_logo ? (
                                <SafeImage src={deal.sponsor_logo} className="w-5 h-5 rounded object-contain border border-slate-100 bg-white" alt="" fallbackText={(deal.sponsor_brand_name || deal.channel_name || "?")} />
                              ) : (
                                <div className="w-5 h-5 rounded bg-slate-100 text-[8px] font-bold text-slate-450 flex items-center justify-center border border-slate-150">{deal.sponsor_name[0]}</div>
                              )}
                              <span className="font-bold text-slate-705 group-hover:text-[#e27b58] transition-colors">{deal.sponsor_name}</span>
                            </div>
                          </td>
                          <td className="py-3.5">
                            <div className="flex items-center gap-2">
                              {deal.channel_avatar ? (
                                <SafeImage src={deal.channel_avatar} className="w-6 h-6 rounded-full object-cover border border-slate-100 bg-white" alt="" fallbackText={(deal.sponsor_brand_name || deal.channel_name || "?")} />
                              ) : (
                                <div className="w-6 h-6 rounded-full bg-slate-100 text-[8px] font-bold text-slate-500 flex items-center justify-center">{deal.channel_name[0]}</div>
                              )}
                              <span className="font-medium text-slate-700">{deal.channel_name}</span>
                            </div>
                          </td>
                          <td className="py-3.5 text-slate-500 line-clamp-1 max-w-xs">{deal.ad_copy}</td>
                          <td className="py-3.5 text-right font-bold text-emerald-600">{Math.round((deal.confidence || 0.95) * 100)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* DETAIL VIEW: DEAL PROFILE                                */}
          {/* ======================================================== */}
          {currentView.page === 'deal-detail' && (
            <div className="space-y-6">
              {detailLoading ? (
                <div className="flex items-center justify-center py-20 text-slate-400">
                  <Loader2 className="w-6 h-6 animate-spin text-[#e27b58] mr-2" /> Loading deal profile...
                </div>
              ) : dealDetail && (
                <>
                  <button 
                    onClick={() => setCurrentView({ page: 'deals', params: {} })}
                    className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-850 font-bold transition-all"
                  >
                    ← Back to Deals
                  </button>

                  {/* Deal Connections Panel */}
                  <div className="glass-panel border border-[#e8e2d9] rounded p-5 flex items-center justify-center gap-8 relative overflow-hidden bg-white shadow-sm">
                    {/* Brand Card */}
                    <div 
                      onClick={() => setCurrentView({ page: 'brand-detail', params: { id: dealDetail.deal.sponsor_id } })}
                      className="border border-[#e8e2d9] bg-slate-50 p-4 rounded flex flex-col items-center justify-center gap-2.5 cursor-pointer hover:border-[#e27b58]/40 w-36 transition-all"
                    >
                      {dealDetail.deal.sponsor_logo ? (
                        <SafeImage src={dealDetail.deal.sponsor_logo} className="w-9 h-9 rounded object-contain border border-[#e8e2d9] bg-white" alt="" fallbackText={(dealDetail.deal.sponsor_brand_name || dealDetail.deal.channel_name || "?")} />
                      ) : (
                        <div className="w-9 h-9 rounded bg-[#f5f2eb] text-lg font-bold text-[#876e5f] flex items-center justify-center">{dealDetail.deal.sponsor_name[0]}</div>
                      )}
                      <span className="text-xs font-black text-slate-700 hover:text-[#e27b58] text-center transition-colors">{dealDetail.deal.sponsor_name}</span>
                    </div>

                    {/* Connection Link Arrow */}
                    <div className="flex flex-col items-center">
                      <span className="text-[10px] text-slate-400 uppercase tracking-wider font-bold mb-1.5">Deal Link</span>
                      <div className="flex items-center gap-1">
                        <div className="w-12 h-0.5 bg-[#e8e2d9]"></div>
                        <ArrowRight className="w-4 h-4 text-[#e27b58]" />
                        <div className="w-12 h-0.5 bg-[#e8e2d9]"></div>
                      </div>
                      <span className="text-xs font-black text-slate-800 mt-1.5 font-serif-title">{dealDetail.estimated_value}</span>
                    </div>

                    {/* Creator Card */}
                    <div 
                      onClick={() => setCurrentView({ page: 'creator-detail', params: { id: dealDetail.deal.channel_id } })}
                      className="border border-[#e8e2d9] bg-slate-50 p-4 rounded flex flex-col items-center justify-center gap-2.5 cursor-pointer hover:border-[#e27b58]/40 w-36 transition-all"
                    >
                      {dealDetail.deal.channel_avatar ? (
                        <SafeImage src={dealDetail.deal.channel_avatar} className="w-9 h-9 rounded-full object-cover border border-[#e8e2d9] bg-white" alt="" fallbackText={(dealDetail.deal.sponsor_brand_name || dealDetail.deal.channel_name || "?")} />
                      ) : (
                        <div className="w-9 h-9 rounded-full bg-[#f5f2eb] text-lg font-bold text-[#876e5f] flex items-center justify-center">{dealDetail.deal.channel_name[0]}</div>
                      )}
                      <span className="text-xs font-black text-slate-700 hover:text-[#e27b58] text-center transition-colors">{dealDetail.deal.channel_name}</span>
                    </div>
                  </div>

                  {/* Main Transcript / Video player vs AI summary layout */}
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Transcript Card */}
                    <div className="lg:col-span-2 space-y-6">
                      <div className="glass-panel border border-[#e8e2d9] rounded p-5 space-y-4 shadow-sm">
                        <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                          <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest">Sponsor Mention Segment</h3>
                          <span className="text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-100 font-bold px-2 py-0.5 rounded">Detected Segment</span>
                        </div>
                        
                        {/* Simulated player / Video card / Newsletter card */}
                        <a 
                          href={dealDetail.deal.source_url || '#'} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className={`w-full ${dealDetail.deal.platform === 'newsletter' ? 'h-48' : 'aspect-video'} rounded bg-slate-50 border border-[#e8e2d9] flex flex-col items-center justify-center relative group overflow-hidden shadow-inner hover:bg-slate-100 transition-colors`}
                        >
                          <div className="absolute inset-0 bg-gradient-to-t from-slate-900/5 to-transparent z-10"></div>
                          
                          {dealDetail.deal.platform === 'newsletter' ? (
                            <Mail className="w-12 h-12 text-[#e27b58] cursor-pointer group-hover:scale-110 transition-transform drop-shadow z-20" />
                          ) : (
                            <Play className="w-12 h-12 text-[#e27b58] fill-[#e27b58] cursor-pointer group-hover:scale-110 transition-transform drop-shadow z-20" />
                          )}
                          
                          <span className="text-xs text-slate-500 mt-2 font-bold z-20">
                            {dealDetail.deal.platform === 'newsletter' ? 'Click to read newsletter archive' : `Click to ${dealDetail.deal.platform === 'youtube' ? 'watch video' : 'listen to audio'}`}
                          </span>
                          
                          <div className="absolute bottom-3 left-3 z-20 flex gap-2">
                            {dealDetail.deal.views > 0 && dealDetail.deal.platform !== 'newsletter' && (
                              <span className="text-[10px] bg-white/90 text-slate-700 px-2 py-0.5 rounded font-black border border-[#e8e2d9] shadow-sm">
                                {dealDetail.deal.views.toLocaleString()} views
                              </span>
                            )}
                            <span className="text-[10px] bg-white/90 text-slate-755 px-2 py-0.5 rounded font-black border border-[#e8e2d9] shadow-sm capitalize">
                              {dealDetail.deal.platform}
                            </span>
                          </div>
                        </a>

                        {/* Transcript Transcript */}
                        <div className="space-y-2">
                          <span className="text-[10px] text-slate-400 uppercase block font-semibold">Transcript Text</span>
                          <p className="text-sm leading-relaxed text-slate-650 font-medium italic bg-[#fbf9f6] p-4 rounded border border-[#e8e2d9]">
                            "{dealDetail.deal.transcript}"
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* AI SUMMARY CARD (THE KILLER) */}
                    <div className="lg:col-span-1 space-y-6">
                      <div className="border border-[#e8e2d9] bg-white rounded p-5 space-y-5 shadow-sm">
                        <div className="flex items-center gap-2 border-b border-[#e8e2d9] pb-3">
                          <Sparkles className="w-4 h-4 text-[#e27b58]" />
                          <h3 className="text-xs font-black text-slate-700 uppercase tracking-widest">AI Sponsorship Summary</h3>
                        </div>

                        <div className="space-y-4">
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase block font-bold">Sponsor Type</span>
                            <span className="text-xs font-bold text-slate-700 block mt-0.5 bg-slate-50 p-2.5 rounded border border-[#e8e2d9]">{dealDetail.ai_summary.sponsor_type}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase block font-bold">Estimated Campaign</span>
                            <span className="text-xs font-bold text-slate-700 block mt-0.5 bg-slate-50 p-2.5 rounded border border-[#e8e2d9]">{dealDetail.ai_summary.estimated_campaign}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase block font-bold">Product Promoted</span>
                            <span className="text-xs font-bold text-slate-700 block mt-0.5 bg-slate-50 p-2.5 rounded border border-[#e8e2d9]">{dealDetail.ai_summary.product}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase block font-bold">Call To Action (CTA)</span>
                            <p className="text-xs text-[#876e5f] font-semibold bg-[#f5f2eb] p-3 rounded border border-[#e8e2d9] leading-relaxed mt-1">
                              {dealDetail.ai_summary.cta}
                            </p>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase block font-bold">Detection Confidence</span>
                            <div className="flex items-center gap-2 mt-1">
                              <div className="flex-1 h-2 rounded bg-slate-100 border border-slate-200 overflow-hidden">
                                <div className="h-full bg-emerald-500" style={{ width: `${Math.round(dealDetail.deal.confidence * 100)}%` }}></div>
                              </div>
                              <span className="text-xs font-bold text-emerald-600">{Math.round(dealDetail.deal.confidence * 100)}%</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ======================================================== */}
          {/* PAGE: RANKINGS (Leaderboards)                           */}
          {/* ======================================================== */}
          {currentView.page === 'rankings' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-black text-slate-900 font-serif-title">Leaderboards & Rankings</h2>
                <p className="text-sm text-slate-400 font-medium mt-1">Global rankings of top marketing spenders and highest-earning creators.</p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Spenders List */}
                <div className="glass-panel border border-[#e8e2d9] rounded p-5 shadow-sm">
                  <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest border-b border-slate-100 pb-2.5 mb-3">Top Spenders (Brands)</h3>
                  <div className="space-y-3">
                    {allSponsors.slice(0, 8).map((sp, idx) => (
                      <div 
                        key={idx} 
                        onClick={() => setCurrentView({ page: 'brand-detail', params: { id: sp.id } })}
                        className="flex items-center justify-between p-2.5 hover:bg-slate-50 rounded cursor-pointer transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-bold text-slate-400 w-4">#{idx+1}</span>
                          <span className="text-sm font-black text-slate-700 hover:text-[#e27b58] transition-colors">{sp.name}</span>
                        </div>
                        <span className="text-sm font-black text-slate-800 font-serif-title">{sp.estimatedSpend}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Creators Earnings List */}
                <div className="glass-panel border border-[#e8e2d9] rounded p-5 shadow-sm">
                  <h3 className="text-xs font-black text-slate-550 uppercase tracking-widest border-b border-slate-100 pb-2.5 mb-3">Top Earnings (Creators)</h3>
                  <div className="space-y-3">
                    {allChannels.slice(0, 8).map((ch, idx) => (
                      <div 
                        key={idx} 
                        onClick={() => setCurrentView({ page: 'creator-detail', params: { id: ch.id } })}
                        className="flex items-center justify-between p-2.5 hover:bg-slate-50 rounded cursor-pointer transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-bold text-slate-400 w-4">#{idx+1}</span>
                          <span className="text-sm font-black text-slate-700 hover:text-[#e27b58] transition-colors">{ch.name}</span>
                        </div>
                        <span className="text-xs font-bold text-slate-500">
                          {formatFollowersCount(ch.followers)} followers
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* PAGE: CATEGORIES (Catalog grid)                          */}
          {/* ======================================================== */}
          {currentView.page === 'categories' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-black text-slate-900 font-serif-title">Marketing Niches</h2>
                <p className="text-sm text-slate-400 font-medium mt-1">Analyze capital allocation structures across core developer market tags.</p>
              </div>

              {/* Categories Catalog */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[
                  { name: 'AI/ML Tools', count: 8, budget: '$420,000', delta: '+21%' },
                  { name: 'Dev Platforms', count: 6, budget: '$350,000', delta: '+14%' },
                  { name: 'Fintech', count: 3, budget: '$180,000', delta: '-8%' },
                  { name: 'Consumer Tech', count: 2, budget: '$90,000', delta: '+4%' },
                  { name: 'SaaS / Tech', count: 3, budget: '$120,000', delta: '+12%' }
                ].map((cat, idx) => (
                  <div key={idx} className="glass-panel border border-[#e8e2d9] rounded p-5 space-y-4 shadow-sm">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-black text-slate-800 font-serif-title">{cat.name}</h3>
                      <span className={`text-[10px] font-black px-2 py-0.5 rounded border ${cat.delta.startsWith('+') ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-rose-50 text-rose-700 border-rose-100'}`}>{cat.delta}</span>
                    </div>
                    <div className="flex justify-between text-xs pt-2.5 border-t border-slate-100">
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase block font-semibold">Active Spenders</span>
                        <span className="text-xs font-bold text-slate-600">{cat.count} brands</span>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] text-slate-400 uppercase block font-semibold">Niche Budget</span>
                        <span className="text-xs font-bold text-slate-800">{cat.budget}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* PAGE: INSIGHTS (AI Generated Marketing Trends)           */}
          {/* ======================================================== */}
          {currentView.page === 'insights' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-black text-slate-900 font-serif-title">AI Marketing Insights</h2>
                <p className="text-sm text-slate-400 font-medium mt-1">Automated trend logs generated directly by parsing current database placements.</p>
              </div>

              {/* Insights Stream */}
              <div className="space-y-4">
                {insights.map((ins) => (
                  <div key={ins.id} className="glass-panel border border-[#e8e2d9] rounded p-5 space-y-3 relative overflow-hidden shadow-sm">
                    <div className="absolute right-4 top-4 opacity-5 pointer-events-none select-none">
                      <Sparkles className="w-16 h-16 text-[#e27b58]" />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] bg-[#f5f2eb] border border-[#e8e2d9] text-[#876e5f] font-bold px-2 py-0.5 rounded">{ins.category}</span>
                      <span className="text-xs text-slate-400 font-semibold">{ins.date}</span>
                    </div>
                    <h3 className="text-sm font-black text-slate-800 font-serif-title">{ins.title}</h3>
                    <p className="text-xs leading-relaxed text-slate-550 font-medium">{ins.body}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* PAGE: SEARCH (Crunchbase Filters)                         */}
          {/* ======================================================== */}
          {currentView.page === 'search' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-black text-slate-900 font-serif-title">Advanced Search</h2>
                <p className="text-sm text-slate-400 font-medium mt-1">Query and filter data points with Crunchbase-style selectors.</p>
              </div>

              {/* Filters Panel */}
              <div className="glass-panel border border-[#e8e2d9] rounded p-5 space-y-4 shadow-sm">
                {/* Search Text */}
                <div className="flex gap-4">
                  <div className="flex-1 relative">
                    <Search className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
                    <input 
                      type="text" 
                      placeholder="Filter by name..." 
                      value={searchText}
                      onChange={(e) => setSearchText(e.target.value)}
                      className="w-full bg-white border border-[#e8e2d9] rounded pl-10 pr-4 py-2.5 text-sm font-semibold text-slate-800 focus:outline-none focus:border-[#e27b58]"
                    />
                  </div>
                  
                  {/* Tab Selector */}
                  <div className="flex bg-slate-50 border border-[#e8e2d9] rounded p-0.5">
                    <button 
                      onClick={() => { setSearchTab('brands'); setSearchText(''); }}
                      className={`px-3 py-1.5 rounded text-[10px] font-black uppercase tracking-wider transition-all ${searchTab === 'brands' ? 'bg-[#e27b58] text-white shadow-sm' : 'text-slate-500 hover:text-slate-850'}`}
                    >
                      Brands
                    </button>
                    <button 
                      onClick={() => { setSearchTab('creators'); setSearchText(''); }}
                      className={`px-3 py-1.5 rounded text-[10px] font-black uppercase tracking-wider transition-all ${searchTab === 'creators' ? 'bg-[#e27b58] text-white shadow-sm' : 'text-slate-500 hover:text-slate-855'}`}
                    >
                      Creators
                    </button>
                  </div>
                </div>

                {/* Multiselect Row */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2.5 border-t border-slate-100">
                  {searchTab === 'brands' ? (
                    <div>
                      <span className="text-[10px] text-slate-450 font-bold block mb-1">Industry</span>
                      <select 
                        value={filterIndustry} 
                        onChange={(e) => setFilterIndustry(e.target.value)}
                        className="w-full bg-white border border-[#e8e2d9] rounded px-2.5 py-1.5 text-sm text-slate-600 focus:outline-none font-semibold"
                      >
                        <option value="All">All Industries</option>
                        <option value="AI/ML Tools">AI/ML Tools</option>
                        <option value="Dev Platforms">Dev Platforms</option>
                        <option value="Fintech">Fintech</option>
                        <option value="Consumer Tech">Consumer Tech</option>
                      </select>
                    </div>
                  ) : (
                    <>
                      <div>
                        <span className="text-[10px] text-slate-450 font-bold block mb-1">Platform</span>
                        <select 
                          value={filterPlatform} 
                          onChange={(e) => setFilterPlatform(e.target.value)}
                          className="w-full bg-white border border-[#e8e2d9] rounded px-2.5 py-1.5 text-sm text-slate-600 focus:outline-none font-semibold"
                        >
                          <option value="All">All Platforms</option>
                          <option value="youtube">YouTube</option>
                          <option value="podcast">Podcast</option>
                          <option value="newsletter">Newsletter</option>
                        </select>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-450 font-bold block mb-1">Country</span>
                        <select 
                          value={filterCountry} 
                          onChange={(e) => setFilterCountry(e.target.value)}
                          className="w-full bg-white border border-[#e8e2d9] rounded px-2.5 py-1.5 text-sm text-slate-650 focus:outline-none font-semibold"
                        >
                          <option value="All">All Countries</option>
                          <option value="US">United States</option>
                          <option value="UK">United Kingdom</option>
                          <option value="CA">Canada</option>
                          <option value="NL">Netherlands</option>
                        </select>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-455 font-bold block mb-1">Followers Tier</span>
                        <select 
                          value={filterFollowers} 
                          onChange={(e) => setFilterFollowers(e.target.value)}
                          className="w-full bg-white border border-[#e8e2d9] rounded px-2.5 py-1.5 text-sm text-slate-650 focus:outline-none font-semibold"
                        >
                          <option value="All">All Ranges</option>
                          <option value="1M">&gt; 1M subscribers</option>
                          <option value="500K">500K - 1M</option>
                          <option value="100K">&lt; 500K</option>
                        </select>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Query Results */}
              <div className="glass-panel border border-[#e8e2d9] rounded p-5 shadow-sm">
                <div className="overflow-x-auto">
                  {searchTab === 'brands' ? (
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="text-slate-450 border-b border-slate-100">
                          <th className="py-2.5 font-bold uppercase text-[10px]">Brand Spender</th>
                          <th className="py-2.5 font-bold uppercase text-[10px]">Industry</th>
                          <th className="py-2.5 font-bold uppercase text-[10px]">Website</th>
                          <th className="py-2.5 font-bold uppercase text-[10px] text-right">Est. Allocation</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {allSponsors
                          .filter(sp => {
                            if (searchText && !sp.name.toLowerCase().includes(searchText.toLowerCase())) return false;
                            if (filterIndustry !== 'All' && sp.industry !== filterIndustry) return false;
                            return true;
                          })
                          .map(sp => (
                            <tr 
                              key={sp.id} 
                              onClick={() => setCurrentView({ page: 'brand-detail', params: { id: sp.id } })}
                              className="hover:bg-slate-50 cursor-pointer group"
                            >
                              <td className="py-3.5">
                                <div className="flex items-center gap-2.5">
                                  {sp.logo_url ? (
                                    <SafeImage src={sp.logo_url} className="w-5 h-5 rounded object-contain border border-slate-100 bg-white" alt="" fallbackText={sp.brand_name || sp.name || "?"} />
                                  ) : (
                                    <div className="w-5 h-5 rounded bg-slate-100 text-[8px] font-bold text-slate-500 flex items-center justify-center border border-slate-150">{sp.name[0]}</div>
                                  )}
                                  <span className="font-bold text-slate-705 group-hover:text-[#e27b58] transition-colors">{sp.name}</span>
                                </div>
                              </td>
                              <td className="py-3.5 text-slate-500 font-bold">{sp.industry}</td>
                              <td className="py-3.5 text-slate-400 font-medium">{sp.website}</td>
                              <td className="py-3.5 text-right font-bold text-slate-800 font-serif-title">{sp.estimatedSpend}</td>
                            </tr>
                          ))
                        }
                      </tbody>
                    </table>
                  ) : (
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="text-slate-450 border-b border-slate-100">
                          <th className="py-2.5 font-bold uppercase text-[10px]">Creator Feed</th>
                          <th className="py-2.5 font-bold uppercase text-[10px]">Platform</th>
                          <th className="py-2.5 font-bold uppercase text-[10px]">Country</th>
                          <th className="py-2.5 font-bold uppercase text-[10px] text-right">Followers</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {allChannels
                          .filter(ch => {
                            if (searchText && !ch.name.toLowerCase().includes(searchText.toLowerCase())) return false;
                            if (filterPlatform !== 'All' && ch.platform !== filterPlatform) return false;
                            if (filterCountry !== 'All' && ch.country !== filterCountry) return false;
                            if (filterFollowers !== 'All') {
                              if (filterFollowers === '1M' && ch.followers < 1000000) return false;
                              if (filterFollowers === '500K' && (ch.followers < 500000 || ch.followers >= 1000000)) return false;
                              if (filterFollowers === '100K' && ch.followers >= 500000) return false;
                            }
                            return true;
                          })
                          .map(ch => (
                            <tr 
                              key={ch.id} 
                              onClick={() => setCurrentView({ page: 'creator-detail', params: { id: ch.id } })}
                              className="hover:bg-slate-50 cursor-pointer group"
                            >
                              <td className="py-3.5">
                                <div className="flex items-center gap-2.5">
                                  {ch.avatar_url ? (
                                    <SafeImage src={ch.avatar_url} className="w-5 h-5 rounded-full object-cover border border-[#e8e2d9] bg-white shadow-sm" alt="" fallbackText={ch.name || "?"} />
                                  ) : (
                                    <div className="w-5 h-5 rounded-full bg-slate-100 text-[8px] font-bold text-slate-500 flex items-center justify-center">{ch.name[0]}</div>
                                  )}
                                  <span className="font-bold text-slate-700 group-hover:text-[#e27b58] transition-colors">{ch.name}</span>
                                </div>
                              </td>
                              <td className="py-3.5">
                                <span className="inline-flex items-center gap-1 bg-slate-50 border border-[#e8e2d9] px-2 py-0.5 rounded text-[10px] text-slate-500 capitalize font-bold">
                                  {getPlatformIcon(ch.platform)}
                                  {ch.platform}
                                </span>
                              </td>
                              <td className="py-3.5 text-slate-500 font-bold">{ch.country || 'US'}</td>
                              <td className="py-3.5 text-right font-bold text-slate-800">{formatFollowersCount(ch.followers)}</td>
                            </tr>
                          ))
                        }
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* PAGE: MONEY MAP (Topology Graph)                          */}
          {/* ======================================================== */}
          {currentView.page === 'money-map' && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-xl font-black text-slate-900 font-serif-title">Money Map</h2>
                  <p className="text-sm text-slate-400 font-medium mt-1">Double-click nodes to view profiles. Hover nodes to view connections.</p>
                </div>
                <div className="flex gap-4 text-xs font-bold">
                  <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-[#e27b58]"></div> Brand</div>
                  <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-emerald-500"></div> Creator</div>
                </div>
              </div>

              {/* Force directed network canvas */}
              <div className="glass-panel border border-[#e8e2d9] rounded overflow-hidden bg-white shadow relative">
                <svg className="w-full h-[560px]">
                  <defs>
                    <marker id="arrow" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                      <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(226, 123, 88, 0.4)" />
                    </marker>
                  </defs>

                  {/* Draw link lines */}
                  {linksState.map((link, idx) => {
                    const srcNode = nodesState.find(n => n.id === link.source);
                    const tgtNode = nodesState.find(n => n.id === link.target);
                    if (!srcNode || !tgtNode) return null;
                    
                    const isHighlighted = hoveredNode && (hoveredNode.id === srcNode.id || hoveredNode.id === tgtNode.id);
                    return (
                      <line
                        key={idx}
                        x1={srcNode.x}
                        y1={srcNode.y}
                        x2={tgtNode.x}
                        y2={tgtNode.y}
                        stroke={isHighlighted ? '#e27b58' : 'rgba(135, 110, 95, 0.08)'}
                        strokeWidth={isHighlighted ? 2.5 : 1.2}
                        markerEnd="url(#arrow)"
                        transition="stroke 0.2s"
                      />
                    );
                  })}

                  {/* Draw nodes circles */}
                  {nodesState.map((node) => {
                    const isBrand = node.type === 'brand';
                    const isHighlighted = hoveredNode && hoveredNode.id === node.id;
                    const size = node.val || 12;
                    
                    return (
                      <g 
                        key={node.id} 
                        transform={`translate(${node.x}, ${node.y})`}
                        onMouseEnter={() => setHoveredNode(node)}
                        onMouseLeave={() => setHoveredNode(null)}
                        onDoubleClick={() => {
                          if (isBrand) {
                            setCurrentView({ page: 'brand-detail', params: { id: node.id } });
                          } else {
                            setCurrentView({ page: 'creator-detail', params: { id: node.id } });
                          }
                        }}
                        className="cursor-pointer group"
                      >
                        <circle
                          r={size}
                          fill={isBrand ? '#e27b58' : '#10b981'}
                          stroke={isHighlighted ? '#191919' : 'rgba(255, 255, 255, 0.3)'}
                          strokeWidth={isHighlighted ? 2.5 : 1}
                          className="transition-all duration-200"
                        />
                        {/* Text Label */}
                        <text
                          y={size + 14}
                          textAnchor="middle"
                          fill={isHighlighted ? '#191919' : '#876e5f'}
                          fontSize="10px"
                          fontWeight={isHighlighted ? '900' : '700'}
                          className="select-none pointer-events-none transition-colors"
                        >
                          {node.label}
                        </text>
                      </g>
                    );
                  })}
                </svg>

                {/* Floating controls hint */}
                <div className="absolute bottom-4 left-4 bg-white/95 border border-[#e8e2d9] p-3 rounded text-[10px] text-slate-500 space-y-1 shadow select-none">
                  <div className="font-bold text-slate-700">Interact Controls:</div>
                  <div>• Hover node to highlight connections</div>
                  <div>• Double-click node to open details</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
