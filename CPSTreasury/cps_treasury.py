from iconservice import *
from .proposal_data import *

PROPOSAL_DB_PREFIX = b'proposal'
TAG = "CPS_TREASURY"


class ProposalAttributes(TypedDict):
    ipfs_hash: str
    project_duration: int
    total_budget: int
    sponsor_reward: int
    contributor_address: Address
    sponsor_address: Address


class CPF_TREASURY_INTERFACE(InterfaceScore):
    @interface
    def disqualify_proposal_fund(self, _ipfs_key: str):
        pass


class CPS_TREASURY(IconScoreBase):
    ID = 'id'
    _PROPOSALS_KEYS = "_proposals_keys"
    _FUND_RECORD = "fund_record"

    _TOTAL_INSTALLMENT_COUNT = "_total_installment_count"
    _TOTAL_TIMES_INSTALLMENT_PAID = "_total_times_installment_paid"
    _TOTAL_TIMES_REWARD_PAID = "_total_times_reward_paid"
    _TOTAL_INSTALLMENT_PAID = "_total_installment_paid"
    _TOTAL_REWARD_PAID = "_total_reward_paid"
    _INSTALLMENT_AMOUNT = "installment_amount"
    _SPONSOR_BOND_AMOUNT = "sponsor_bond_amount"

    _CPS_SCORE = "_cps_score"
    _CPF_TREASURY_SCORE = "_cpf_treasury_score"

    _SPONSOR_ADDRESS = "sponsor_address"
    _CONTRIBUTOR_ADDRESS = "contributor_address"
    _STATUS = "status"
    _IPFS_HASH = "ipfs_hash"
    _SPONSOR_REWARD = "sponsor_reward"
    _TOTAL_BUDGET = "total_budget"

    _ACTIVE = "active"
    _DISQUALIFIED = "disqualified"
    _COMPLETED = "completed"

    @eventlog(indexed=1)
    def ProposalFundDeposited(self, _ipfs_key: str, _total_budget: int, note: str):
        pass

    @eventlog(indexed=1)
    def ProposalFundSent(self, _receiver_address: Address, _fund: int, note: str):
        pass

    @eventlog(indexed=1)
    def ProposalFundWithdrawn(self, _receiver_address: Address, _fund: int, note: str):
        pass

    @eventlog(indexed=1)
    def ProposalDisqualified(self, _ipfs_key: str, note: str):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)

        self.id = VarDB(self.ID, db, value_type=str)
        self.proposals = ProposalDataDB(db)

        self._proposals_keys = ArrayDB(self._PROPOSALS_KEYS, db, value_type=str)
        self._fund_record = DictDB(self._FUND_RECORD, db, value_type=int)

        self._cpf_treasury_score = VarDB(self._CPF_TREASURY_SCORE, db, value_type=Address)
        self._cps_score = VarDB(self._CPS_SCORE, db, value_type=Address)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def name(self) -> str:
        """
        :return: SCORE Name
        :rtype: str
        """
        return TAG

    @payable
    def fallback(self):
        revert(f"{TAG} : ICX can only be sent by CPF Treasury Score.")

    def set_id(self, _val: str):
        self.id.set(_val)

    def get_id(self) -> str:
        return self.id.get()

    def proposal_prefix(self, _proposal_key: str) -> bytes:
        return b'|'.join([PROPOSAL_DB_PREFIX, self.id.get().encode(), _proposal_key.encode()])

    def _validate_owner(self):
        if self.msg.sender != self.owner:
            revert(f"{TAG} :Only owner can call this method.")

    def _validate_owner_score(self, _score: Address):
        self._validate_owner()
        if not _score.is_contract:
            revert(f"{TAG} :Target({_score}) is not SCORE.")

    def _validate_cps_score(self):
        if self.msg.sender != self._cps_score.get():
            revert(f"{TAG} :Only CPS({self._cps_score.get()}) SCORE can send fund using this method.")

    def _validate_cpf_treasury_score(self):
        if self.msg.sender != self._cpf_treasury_score.get():
            revert(
                f"{TAG} :Only CPF Treasury({self._cpf_treasury_score.get()}) SCORE can send fund using this method.")

    def _add_record(self, _proposal: ProposalAttributes) -> None:
        proposal_data_obj = createProposalDataObject(_proposal)
        if proposal_data_obj.ipfs_hash not in self._proposals_keys:
            self._proposals_keys.put(proposal_data_obj.ipfs_hash)
            prefix = self.proposal_prefix(proposal_data_obj.ipfs_hash)
            addDataToProposalDB(prefix, self.proposals, proposal_data_obj)
        else:
            revert(f"{TAG} : Already have this project.")

    def _get_projects(self, _proposal_key: str) -> dict:
        prefix = self.proposal_prefix(_proposal_key)
        _proposal_details = getDataFromProposalDB(prefix, self.proposals)
        return _proposal_details

    @external
    def set_cps_score(self, _score: Address) -> None:
        """
        Sets the cps score address. Only owner can set the address.
        :param _score: Address of the cps score address
        :type _score: :class:`iconservice.base.address.Address`
        :return:
        """
        self._validate_owner_score(_score)
        self._cps_score.set(_score)

    @external(readonly=True)
    def get_cps_score(self) -> Address:
        """
        Returns the cps score address
        :return: cps score address
        :rtype: :class:`iconservice.base.address.Address`
        """
        return self._cps_score.get()

    @external
    def set_cpf_treasury_score(self, _score: Address) -> None:
        """
        Sets the cpf treasury score address. Only owner can set the address.
        :param _score: Address of the cpf treasury score address
        :type _score: :class:`iconservice.base.address.Address`
        :return:
        """
        self._validate_owner_score(_score)
        self._cpf_treasury_score.set(_score)

    @external(readonly=True)
    def get_cpf_treasury_score(self) -> Address:
        """
        Returns the cpf treasury score address
        :return: cpf treasury score address
        :rtype: :class:`iconservice.base.address.Address`
        """
        return self._cpf_treasury_score.get()

    @external(readonly=True)
    def get_contributor_projected_fund(self, _wallet_address: Address) -> dict:
        """
        Return the projected amount to be obtained on the end of voting period
        :param _wallet_address: wallet address of the contributor
        :return:
        """
        _total_amount_to_be_paid = 0
        _installment_amount = []
        for _ipfs_key in self._proposals_keys:
            prefix = self.proposal_prefix(_ipfs_key)
            if self.proposals[prefix].status.get() != self._DISQUALIFIED:
                if self.proposals[prefix].contributor_address.get() == _wallet_address:
                    _total_installment = self.proposals[prefix].project_duration.get()
                    _total_paid_count = self.proposals[prefix].installment_count.get()
                    if _total_paid_count < _total_installment:
                        _total_budget = self.proposals[prefix].total_budget.get()
                        _total_paid_amount = self.proposals[prefix].withdraw_amount.get()

                        _installment_amount.append({self._IPFS_HASH: _ipfs_key,
                                                    self._TOTAL_BUDGET: _total_budget,
                                                    self._TOTAL_INSTALLMENT_PAID: _total_paid_amount,
                                                    self._TOTAL_INSTALLMENT_COUNT: _total_installment,
                                                    self._TOTAL_TIMES_INSTALLMENT_PAID: _total_paid_count,
                                                    self._INSTALLMENT_AMOUNT: _total_budget // _total_installment})
                        _total_amount_to_be_paid += _total_budget // _total_installment

        _withdraw_amount = self._fund_record[str(_wallet_address)] if _total_amount_to_be_paid > 0 else 0
        return {"data": _installment_amount,
                "project_count": len(_installment_amount),
                "total_amount": _total_amount_to_be_paid,
                "withdraw_amount": _withdraw_amount}

    @external(readonly=True)
    def get_sponsor_projected_fund(self, _wallet_address: Address) -> dict:
        """
        Return the projected sponsor reward to be obtained on the end of voting period
        :param _wallet_address: wallet address of the sponsor p-rep
        :return:
        """
        _total_amount_to_be_paid = 0
        _total_sponsor_bond = 0
        _installment_amount = []
        for _ipfs_key in self._proposals_keys:
            prefix = self.proposal_prefix(_ipfs_key)
            if self.proposals[prefix].status.get() != self._DISQUALIFIED:
                if self.proposals[prefix].sponsor_address.get() == _wallet_address:
                    _total_installment = self.proposals[prefix].project_duration.get()
                    _total_paid_count = self.proposals[prefix].sponsor_reward_count.get()
                    if _total_paid_count < _total_installment:
                        _total_budget = self.proposals[prefix].sponsor_reward.get()
                        _total_paid_amount = self.proposals[prefix].sponsor_withdraw_amount.get()
                        _deposited_sponsor_bond = self.proposals[prefix].total_budget.get() // 10

                        _installment_amount.append({self._IPFS_HASH: _ipfs_key,
                                                    self._SPONSOR_REWARD: _total_budget,
                                                    self._TOTAL_INSTALLMENT_PAID: _total_paid_amount,
                                                    self._TOTAL_INSTALLMENT_COUNT: _total_installment,
                                                    self._TOTAL_TIMES_INSTALLMENT_PAID: _total_paid_count,
                                                    self._INSTALLMENT_AMOUNT: _total_budget // _total_installment,
                                                    self._SPONSOR_BOND_AMOUNT: _deposited_sponsor_bond})
                        _total_amount_to_be_paid += _total_budget // _total_installment
                        _total_sponsor_bond += _deposited_sponsor_bond

        _withdraw_amount = self._fund_record[str(_wallet_address)] if _total_amount_to_be_paid > 0 else 0

        return {"data": _installment_amount,
                "project_count": len(_installment_amount),
                "total_amount": _total_amount_to_be_paid,
                "withdraw_amount": _withdraw_amount,
                "total_sponsor_bond": _total_sponsor_bond}

    @external
    @payable
    def deposit_proposal_fund(self, _proposals: ProposalAttributes) -> None:
        """
        Treasury Score sending the amount to the CPS Treasury Score
        :ipfs_hash: Proposal IPFS HASH key
        :project_duration: Total Duration month count
        :sponsor_address: Sponsor P-Rep Address
        :contributor_address: Contributor Address
        :total_budget: Total Budget for the project (LOOP)
        :sponsor_reward: Reward for the Sponsor (Loop)
        """

        self._validate_cpf_treasury_score()

        proposal_key = _proposals.copy()
        proposal_key[self._STATUS] = self._ACTIVE

        self._add_record(proposal_key)
        self.ProposalFundDeposited(proposal_key[self._IPFS_HASH], proposal_key[self._TOTAL_BUDGET],
                                   f"Received {self.msg.value} fund from CPF.")

    @external
    @payable
    def update_proposal_fund(self, _ipfs_key: str, _added_budget: int = 0, _added_sponsor_reward: int = 0,
                             _added_installment_count: int = 0) -> None:
        """
        After the budget adjustment is successfully approved. The added budget will be transferred from CPF
        :param _added_sponsor_reward: After budget adjustment, 2% of the total fund added for sponsor

        :param _ipfs_key: Proposal IPFS HASH key
        :param _added_budget: added budget
        :type _added_budget: int
        :param _added_installment_count: Added duration in month
        :type _added_installment_count: int
        :return:
        """
        self._validate_cpf_treasury_score()

        prefix = self.proposal_prefix(_ipfs_key)
        _total_budget: int = self.proposals[prefix].total_budget.get()
        _sponsor_reward: int = self.proposals[prefix].sponsor_reward.get()
        _total_duration: int = self.proposals[prefix].project_duration.get()

        if _ipfs_key in self._proposals_keys:
            self.proposals[prefix].total_budget.set(_total_budget + _added_budget)
            self.proposals[prefix].sponsor_reward.set(_sponsor_reward + _added_sponsor_reward)
            self.proposals[prefix].project_duration.set(_total_duration + _added_installment_count)

            self.ProposalFundDeposited(_ipfs_key, _added_budget,
                                       f"{_ipfs_key} : Added Budget : {_added_budget} Successfully")
        else:
            revert(f"{TAG} : IPFS Hash doesn't exist")

    @external
    def send_installment_to_contributor(self, _ipfs_key: str) -> None:
        """
        Installment of the Proposal is send to the contributor after the progress report is approved by majority
        registered P-Rep(s)
        :param _ipfs_key: Proposal IPFS HASH key
        :return:
        """
        self._validate_cps_score()

        if _ipfs_key in self._proposals_keys:
            prefix = self.proposal_prefix(_ipfs_key)
            proposal = self.proposals[prefix]

            _installment_count: int = proposal.installment_count.get()
            withdraw_amount: int = proposal.withdraw_amount.get()
            remaining_amount: int = proposal.remaining_amount.get()
            contributor_address: 'Address' = proposal.contributor_address.get()

            # Calculating Installment Amount and adding to Wallet Address
            try:
                if _installment_count == 1:
                    _installment_amount = remaining_amount
                else:
                    _installment_amount = remaining_amount // _installment_count
                proposal.installment_count.set(_installment_count - 1)
                proposal.remaining_amount.set(remaining_amount - _installment_amount)
                proposal.withdraw_amount.set(withdraw_amount + _installment_amount)
                self._fund_record[str(contributor_address)] += _installment_amount

                self.ProposalFundSent(contributor_address, _installment_amount,
                                      f"New Installment sent to contributors address.")

                if proposal.installment_count.get() == 0:
                    proposal.status.set(self._COMPLETED)

            except BaseException as e:
                revert(f'{TAG}: Network problem. Sending project funds. {e}')

    @external
    def send_reward_to_sponsor(self, _ipfs_key: str) -> None:
        """
        Installment of the Sponsor Reward is send to the Sponsor P-Rep after the Proposal's progress report is
        approved by majority registered P-Rep(s)
        :param _ipfs_key: Proposal IPFS HASH key
        :return:
        """
        self._validate_cps_score()

        if _ipfs_key in self._proposals_keys:
            prefix = self.proposal_prefix(_ipfs_key)
            proposals = self.proposals[prefix]

            _sponsor_reward_count: int = proposals.sponsor_reward_count.get()
            _sponsor_withdraw_amount: int = proposals.sponsor_withdraw_amount.get()
            _sponsor_remaining_amount: int = proposals.sponsor_remaining_amount.get()
            _sponsor_address: 'Address' = proposals.sponsor_address.get()

            # Calculating Installment Amount and adding to Wallet Address
            try:
                if _sponsor_reward_count == 1:
                    _installment_amount = _sponsor_remaining_amount
                else:
                    _installment_amount = _sponsor_remaining_amount // _sponsor_reward_count
                proposals.sponsor_reward_count.set(_sponsor_reward_count - 1)
                proposals.sponsor_withdraw_amount.set(_sponsor_withdraw_amount + _installment_amount)
                proposals.sponsor_remaining_amount.set(_sponsor_remaining_amount - _installment_amount)
                self._fund_record[str(_sponsor_address)] += _installment_amount

                self.ProposalFundSent(_sponsor_address, _installment_amount,
                                      f"New Installment sent to sponsor address.")

                if proposals.sponsor_reward_count.get() == 0:
                    proposals.status.set(self._COMPLETED)
            except BaseException as e:
                revert(f"{TAG} : Network problem. Sending project funds. {e}")

    @external
    def disqualify_project(self, _ipfs_key: str) -> None:
        """
        In case, Contributor fails to pass the progress report twice in a row, the project get disqualified.
        The remaining amount of the project is sent back to the CPF.
        :param _ipfs_key: Proposal IPFS HASH key
        """
        self._validate_cps_score()

        if _ipfs_key in self._proposals_keys:
            prefix = self.proposal_prefix(_ipfs_key)
            proposals = self.proposals[prefix]

            # Set Proposal status to disqualified
            proposals.status.set(self._DISQUALIFIED)

            _total_budget = proposals.total_budget.get()
            _withdraw_amount = proposals.withdraw_amount.get()
            _sponsor_reward = proposals.sponsor_reward.get()
            _sponsor_withdraw_amount = proposals.sponsor_withdraw_amount.get()

            _remaining_budget = _total_budget - _withdraw_amount
            _remaining_reward = _sponsor_reward - _sponsor_withdraw_amount

            # return remaining fund amount to the CPF
            try:
                cpf_treasury_score = self.create_interface_score(self._cpf_treasury_score.get(), CPF_TREASURY_INTERFACE)
                cpf_treasury_score.icx(_remaining_budget + _remaining_reward).disqualify_proposal_fund(
                    _ipfs_key)

                self.ProposalDisqualified(_ipfs_key, f"{_ipfs_key}, Proposal disqualified")
            except BaseException as e:
                revert(f"{TAG} : Network problem. Sending proposal funds. {e}")
        else:
            revert(f"{TAG} : Provided IPFS key not found.")

    @external
    def claim_reward(self) -> None:
        """
        Claim he reward or the installment amount
        """
        _available_amount = self._fund_record[str(self.msg.sender)]
        if _available_amount > 0:
            try:
                # set the remaining fund 0
                self._fund_record[str(self.msg.sender)] = 0

                self.icx.transfer(self.msg.sender, _available_amount)
                self.ProposalFundWithdrawn(self.msg.sender, _available_amount, f"{_available_amount} withdrawn to "
                                                                               f"{self.msg.sender}")
            except BaseException as e:
                revert(f"{TAG} : Network problem. Claiming Reward{e}")

        else:
            revert(f"{TAG} :Claim Reward Fails. Available Amount = {_available_amount}.")
