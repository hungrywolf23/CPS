const PERIOD_MAPPINGS = {
  APPLICATION_PERIOD: "Application Period",
  VOTING_PERIOD: "Voting Period",
  TRANSITION_PERIOD: "Transition Period",
}

const PROPOSAL_STATUS = {
  PENDING: '_pending',
  ACTIVE: '_active',
  PAUSED: '_paused',
  COMPLETED: '_completed',
  DISQUALIFIED: '_disqualified',
  REJECTED: '_rejected',
}

const PROGRESS_REPORT_STATUS = {
  WAITING: '_waiting',
  APPROVED: '_approved',
}

const EVENT_TYPES = {
  PROPOSAL_STATS: 'proposalStats',
  PROGRESS_REPORT_STATS: 'prStats',
  VOTING_PERIOD_STATS: 'votingPeriodStats',
  APPLICATION_PERIOD_STATS: 'applicationPeriodStats',
}

const IPFS_BASE_URL = 'https://gateway.ipfs.io/ipfs/';

const SUBSCRIPTION_KEY = 'botSubscriber';

module.exports = {
  PERIOD_MAPPINGS,
  PROPOSAL_STATUS,
  PROGRESS_REPORT_STATUS,
  EVENT_TYPES,
  IPFS_BASE_URL,
  SUBSCRIPTION_KEY,
}