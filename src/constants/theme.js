export const COLORS = {
  navy: '#0B1D3A',
  deepBlue: '#102A4C',
  ice: '#C8E6F5',
  frost: '#E8F4FC',
  electric: '#00A6ED',
  electricDark: '#0082BD',
  amber: '#F5A623',
  white: '#FFFFFF',
  snow: '#F7FAFC',
  slate: '#475569',
  darkSlate: '#1E293B',
  midnightGreen: '#0A3042',
  teal: '#0D9488',
  warm: '#FFF8F0',
};

export const NAV_ITEMS = [
  { id: 'home', label: 'Home', icon: '\u2302' },
  { id: 'team', label: 'Team', icon: '\u25CE' },
  { id: 'workshops', label: 'Workshops', icon: '\u25C8' },
  { id: 'data-tools', label: 'Data & Tools', icon: '\uD83D\uDD27' },
  { id: 'news', label: 'News', icon: '\u25C9' },
  { id: 'calendar', label: 'Calendar', icon: '\u25A6' },
  { id: 'login', label: 'Login', icon: '\u22A1' },
];

export const TEAM_CORE = [
  { name: 'Ana Dyreson', role: 'Principal Investigator', org: 'Michigan Tech', interests: 'Climate-informed energy planning, electric power resilience, community-engaged research', link: 'https://www.mtu.edu' },
  { name: 'Chelsea Schelly', role: 'Co-Principal Investigator', org: 'Michigan Tech', interests: 'Social science of energy transitions, stakeholder engagement, rural communities', link: 'https://www.mtu.edu' },
  { name: 'Pengfei Xue', role: 'Co-Principal Investigator', org: 'Michigan Tech', interests: 'Earth system modeling, Great Lakes regional climate, lake-effect weather', link: 'https://www.mtu.edu' },
  { name: 'Vivek Srikrishnan', role: 'Co-Principal Investigator', org: 'Cornell University', interests: 'Climate risk management, winter climate trend analyses, decision-making under uncertainty', link: 'https://www.cornell.edu' },
];

export const TEAM_PLANNING = [
  { name: 'Anna Stuhlmacher', role: 'Supporting Expert', org: 'MTU', interests: 'Regional economic modeling, energy systems analysis', link: 'https://www.mtu.edu' },
  { name: 'Chee-Wooi Ten', role: 'Supporting Expert', org: 'MTU', interests: 'Power systems cybersecurity, smart grid infrastructure', link: 'https://www.mtu.edu' },
  { name: 'David Watkins', role: 'Supporting Expert', org: 'MTU', interests: 'Scenario development, water resources engineering', link: 'https://www.mtu.edu' },
  { name: 'Jenny Apriesnig', role: 'Supporting Expert', org: 'MTU', interests: 'Regional economic modeling, cost-benefit analysis', link: 'https://www.mtu.edu' },
  { name: 'Jiali Wang', role: 'Committee Member', org: 'ANL', interests: 'Climate modeling, regional weather analysis', link: 'https://www.anl.gov' },
  { name: 'Josh Quinnell', role: 'Committee Member', org: 'CEE', interests: 'Building energy efficiency, community energy systems', link: 'https://www.mncee.org' },
  { name: 'Venkat Canunarayanan', role: 'Committee Member', org: 'NRECA', interests: 'Rural electric cooperative operations, utility resilience', link: 'https://www.electric.coop' },
];

export const ORGANIZATIONS = [
  { name: 'Argonne National Laboratory', abbr: 'ANL', desc: 'Climate modeling and computational science for resilience analysis' },
  { name: 'Minnesota Center for Energy and Environment', abbr: 'CEE', desc: 'Building energy efficiency and community energy programs' },
  { name: 'National Rural Electric Cooperative Association', abbr: 'NRECA', desc: 'Representing and supporting America\'s electric cooperatives' },
  { name: 'National Laboratory of the Rockies', abbr: 'NLR', desc: 'Energy systems research and data infrastructure' },
  { name: 'Michigan Technological University', abbr: 'MTU', desc: 'Lead institution \u2014 power systems, Earth system science, social science' },
  { name: 'Cornell University', abbr: 'CU', desc: 'Climate risk management and winter climate trends' },
  { name: 'University of Wisconsin\u2013Madison', abbr: 'WI-Madison', desc: 'Energy systems engineering and Midwest regional expertise' },
];

export const WORKSHOPS = [
  { id: 1, title: 'Future Winter Weather: What We Know & Don\'t Know', desc: 'Exploring current understanding and uncertainties in future winter weather projections for the Midwest, including extreme cold, lake-effect snow, and ice storms.', status: 'upcoming', date: 'TBD \u2014 Fall 2026' },
  { id: 2, title: 'Equity in Electricity Investments for Rural Utilities', desc: 'Understanding how equity considerations should inform resilience investments for small municipal and cooperative utilities serving rural communities.', status: 'planned', date: 'TBD \u2014 Winter 2027' },
  { id: 3, title: 'Solar PV & Heat Pumps in Northern Climates', desc: 'Examining tradeoffs in new technology adoption \u2014 snow impacts on PV, heat pump demand shifts, and planning for winter peak loads.', status: 'planned', date: 'TBD \u2014 Spring 2027' },
  { id: 4, title: 'Lake-Effect Weather, Climate & Electric Power', desc: 'The science of lake-effect weather systems and their unique impacts on electric power infrastructure in the Great Lakes region.', status: 'planned', date: 'TBD \u2014 Summer 2027' },
];

export const NEWS_ITEMS = [
  { id: 1, title: 'NSF Awards R2I2 Grant for Winter Resilience Research', date: 'August 2025', summary: 'Michigan Tech leads a new NSF-funded project to translate Earth system science for winter-resilient electric power systems in the Midwest.', tag: 'Award' },
  { id: 2, title: 'Planning Committee Kickoff Meeting', date: 'March 2026', summary: 'The inaugural planning committee convened to set workshop themes, establish timelines, and define stakeholder engagement strategies.', tag: 'Milestone' },
  { id: 3, title: 'Stakeholder Outreach Begins Across Midwest', date: '2026', summary: 'The project team is actively reaching out to cooperative and municipal utilities across eight Midwest states to participate in upcoming workshops.', tag: 'Outreach' },
  { id: 4, title: 'R2I2 National Program Overview', date: '2025', summary: 'Learn about the broader NSF R2I2 program connecting regional incubators nationwide to build resilient infrastructure for communities.', tag: 'Program' },
];

export const TOOLS_LIST = [
  { name: 'Rural Hazard Resilience Tools (RHRT)', link: 'https://www.wuppdr.org/rhrt', desc: 'Interactive mapping and risk assessment for rural communities facing natural hazards.' },
  { name: 'ClimRR Local Projections', link: 'https://climrr.anl.gov/localprojections', desc: 'Climate risk and resilience projections at local scales from Argonne National Laboratory.' },
  { name: 'Open Infrastructure Map', link: 'https://openinframap.org/#3.58/37.88/-100.36', desc: 'Open-source interactive map of power infrastructure, transmission lines, and substations.' },
  { name: 'R2I2 National Project Map', link: 'https://r2i2.umn.edu/r2i2-project-teams/project-map', desc: 'Map of all R2I2 project teams across the United States.' },
];

export const DATA_PORTALS = [
  { name: 'NASA Earthdata', link: 'https://earthdata.nasa.gov/' },
  { name: 'NOAA Climate Data', link: 'https://www.ncei.noaa.gov/' },
  { name: 'FERC Utility Data', link: 'https://www.ferc.gov/industries-data' },
  { name: 'NERC Reliability Data', link: 'https://www.nerc.com/pa/RAPA/Pages/default.aspx' },
  { name: 'Michigan DNR', link: 'https://www.michigan.gov/dnr' },
  { name: 'Data.gov Energy', link: 'https://catalog.data.gov/' },
];

export const initials = (name) => name.split(' ').map(w => w[0]).join('');
