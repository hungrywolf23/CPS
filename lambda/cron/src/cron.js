const BigNumber = require('bignumber.js');
const axios = require('axios');
const score = require('./score');
const { PERIOD_MAPPINGS, PROPOSAL_STATUS, PROGRESS_REPORT_STATUS, EVENT_TYPES, IPFS_BASE_URL } = require('./constants');
const { sleep, triggerWebhook } = require('./utils');

const DAY = 24 * 60 * 60;


async function formatProposalDetailsResponse(allProposals) {
	
	// ==============================BUILD RESPONSE FOR PROPOSALS DETAILS==============================
	const response = {
		approvedProposals: [],
		rejectedProposals: [],
		pausedProposals: [],
		disqualifiedProposals: [],
		completedProposals: [],
	}

	for(proposal of allProposals) {
		// fetch teamName and sponsorName
		
		let proposalDetails;
		try {
				proposalDetails = await axios.get(IPFS_BASE_URL + proposal.ipfs_hash);
		} catch (err) {
				console.error("ERROR FETCHING PROPOSAL DATA" + JSON.stringify(err));
				throw { statusCode: 400, name: "IPFS url", message: "Invalid IPFS hash provided" };
		}

		const {teamName, sponserPrepName } = proposalDetails.data;

		const proposalRes = {
			proposalName: proposal.project_title,
			totalBudget: proposal.total_budget,
			teamName: teamName,
			sponsorAddress: proposal.sponsor_address,
			sponsorName: sponserPrepName,
			sponsorVoteReason: proposal.sponsor_vote_reason,
		}

		switch(proposal.status) {
			case PROPOSAL_STATUS.ACTIVE: {
				const approvedProposalDetails = {
					...proposalRes,
					approvingVoters: new BigNumber(proposal.approve_voters).toFixed(0),
					approvingVotersPercentage: new BigNumber(proposal.total_voters).toNumber() > 0 ?
							new BigNumber(proposal.approve_voters).dividedBy(proposal.total_voters).toFixed(2, 1)
							:
							'0',
					approvedVotes: new BigNumber(proposal.approved_votes).toFixed(0),
					approvedVotesPercentage: new BigNumber(proposal.total_votes) > 0 ?
							new BigNumber(proposal.approved_votes).dividedBy(proposal.total_votes).toFixed(2,1)
							:
							'0',
				};
				response.approvedProposals.push(approvedProposalDetails);
				break;
			}
			
			case PROPOSAL_STATUS.REJECTED: {
				const rejectedProposalDetails = {
					...proposalRes,
					rejectingVoters: new BigNumber(proposal.reject_voters).toFixed(0),
					rejectingVotersPercentage: new BigNumber(proposal.total_voters).toNumber() > 0 ?
							new BigNumber(proposal.reject_voters).dividedBy(proposal.total_voters).toFixed(2, 1)
							:
							'0',
					rejectedVotes: new BigNumber(proposal.rejected_votes).toFixed(0),
					rejectedVotesPercentage: new BigNumber(proposal.total_votes) > 0 ?
							new BigNumber(proposal.rejected_votes).dividedBy(proposal.total_votes).toFixed(2,1)
							:
							'0',
					abstainingVoters: new BigNumber(proposal.total_voters)
						.minus(proposal.approve_voters)
						.minus(proposal.reject_voters)
						.toFixed(0),
					abstainedVotes: new BigNumber(proposal.total_votes)
						.minus(proposal.approved_votes)
						.minus(proposal.rejected_votes)
						.toFixed(0),
				};
				response.rejectedProposals.push(rejectedProposalDetails);
				break;
			}

			case PROPOSAL_STATUS.PAUSED: {
				response.pausedProposals.push(proposalRes);
			}
			
			case PROPOSAL_STATUS.DISQUALIFIED: {
				response.disqualifiedProposals.push(proposalRes);
			}

			case PROPOSAL_STATUS.COMPLETED: {
				response.completedProposals.push(proposalRes);
			}
		}

		return response;
	}
}


async function execute() {
	let actions = [];
	try {

		//code block to trigger the period change
		let period_triggered = false;

		let present_period = await score.period_check();
		// transition is as : voting -> transition -> application
		console.log('Period from Blockchain' + JSON.stringify(present_period));
		
		// TODO: Remove this
		console.log(present_period.remaining_time);
		
		if (parseInt(present_period.remaining_time, 'hex') === 0) {
			// if current period is "Voting Period" -> update_period moves it to transition period
			// wait for 20 secs, then again trigger the update_period if the current period is transition period
			// then verify that the period is now application period
			console.log('Period updated');
			await score.update_period();
			period_triggered = true;
			await sleep(2000);	// sleep for 2 secs
			present_period = await score.period_check();
			console.log('Changed period to: ' + present_period['period_name']);

			if(present_period['period_name'] == PERIOD_MAPPINGS.TRANSITION_PERIOD) {
				await score.recursivelyUpdatePeriod();
			}

			const periodEndingDate = new Date();
			periodEndingDate.setDate(periodEndingDate.getDate() + 15);

			// ========================================CPS BOT TRIGGERS=========================================

			if(present_period['period_name'] == PERIOD_MAPPINGS.APPLICATION_PERIOD) {
				// Send out last voting period's stats
				const remainingFunds = await score.get_remaining_funds();
				const activeProjectAmt = await score.get_project_amounts_by_status(PROPOSAL_STATUS.ACTIVE);
				const votingPeriodStats = {
					remainingFunds: new BigNumber(remainingFunds).div(Math.pow(10,18)).toFixed(2),
					periodEndsOn: periodEndingDate.getTime().toString(),
					projectsCount: new BigNumber(activeProjectAmt['_count']).toFixed(),
					totalProjectsBudget: new BigNumber(activeProjectAmt['_total_amount']).div(Math.pow(10, 18)).toFixed(2)
				};
				await triggerWebhook(EVENT_TYPES.VOTING_PERIOD_STATS, votingPeriodStats);

				// ------Send out details different proposals by category-----

				// get proposals by status
				const allApprovedProposals = await score.getProposalDetailsByStatus(PROPOSAL_STATUS.ACTIVE);
				const approvedProposals = allApprovedProposals.filter(proposal => parseInt(proposal.percentage_completed, 16) == 0);
				const rejectedProposals = await score.getProposalDetailsByStatus(PROPOSAL_STATUS.REJECTED, true);
				const pausedProposals = await score.getProposalDetailsByStatus(PROPOSAL_STATUS.PAUSED, true);
				const disqualifiedProposals = await score.getProposalDetailsByStatus(PROPOSAL_STATUS.DISQUALIFIED, true);
				const completedProposals = await score.getProposalDetailsByStatus(PROPOSAL_STATUS.COMPLETED, true);

				const formattedProposalDetails = formatProposalDetailsResponse(approvedProposals.concat(rejectedProposals).concat(pausedProposals).concat(disqualifiedProposals).concat(completedProposals));

				await triggerWebhook(EVENT_TYPES.PROPOSAL_STATS, formattedProposalDetails);
			}

			// Send out last application period's stats
			if(present_period['period_name'] == PERIOD_MAPPINGS.VOTING_PERIOD) {
				const pendingProjectAmt = await score.get_project_amounts_by_status(PROPOSAL_STATUS.PENDING);
				const waitingProgressReportCount = await score.get_progress_reports_by_status(PROGRESS_REPORT_STATUS.WAITING);
				const applicationPeriodStats = {
					votingProposalsCount: new BigNumber(pendingProjectAmt['_count']).toFixed(),
					votingProposalsBudget: new BigNumber(activeProjectAmt['_total_amount']).toFixed(),
					periodEndsOn: periodEndingDate.getTime().toString(),
					votingPRsCount: new BigNumber(waitingProgressReportCount['count']).toFixed(),
				};
				triggerWebhook(EVENT_TYPES.APPLICATION_PERIOD_STATS, applicationPeriodStats);
			}
		}
		// ===================================================================================================
	} catch (err) {
		throw err;
	}
}

module.exports = { execute };