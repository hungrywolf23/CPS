import React, {useState} from 'react';
import { Row } from 'react-bootstrap';
import styles from './Header.module.css'
import { Button } from 'react-bootstrap';
import { connect } from 'react-redux';
import { logout } from '../../Redux/Reducers/accountSlice';
import {unregisterPrep, registerPrep} from 'Redux/Reducers/prepsSlice';
import ConfirmationModal from 'Components/UI/ConfirmationModal';
import UserInfoFormModal from './UserInfoFormModal';
import useTimer from 'Hooks/useTimer';

const Header = ({ address, logout, title, isPrep, isRegistered, unregisterPrep, registerPrep,period, payPenalty, firstName, lastName }) => {

    const [modalShow, setModalShow] = React.useState(false);

    const {isRemainingTimeZero} = useTimer();

    const onLogout = () => {
        logout();
    }

    const [showUnregisterConfirmationModal, setShowUnregisterConfirmationModal] = useState(false);

    const onClickUnregisterPrep = () => {
        unregisterPrep();
    }

    const onClickRegisterPrep = () => {
        registerPrep();
    }

    return (
        <Row className = {styles.headerContainer} >
            <span className={styles.heading}>{title}</span>

            <div className={styles.account}>
                <span onClick={() => setModalShow(true)} className = {styles.address }>{(firstName || lastName) ? `${firstName || ''} ${lastName || ''}` : `${address.slice(0,4)}...${address.slice(address.length-2)}`}</span>
                {
                    isPrep && isRegistered && !payPenalty && period === 'APPLICATION' && !isRemainingTimeZero &&
                    <Button variant="danger" onClick={() => setShowUnregisterConfirmationModal(true)} style = {{marginRight: '5px', marginLeft: '5px'}}>Unregister Prep</Button>

                }

{
                    isPrep && !isRegistered && !payPenalty && period === 'APPLICATION' && !isRemainingTimeZero &&
                    <Button variant="success" onClick={() => setShowUnregisterConfirmationModal(true)} style = {{marginRight: '5px', marginLeft: '5px'}}>Register Prep</Button>

                }

                <Button variant="info" onClick={onLogout}>Logout</Button>
            </div>

            <ConfirmationModal
                show={showUnregisterConfirmationModal}
                onHide={() => setShowUnregisterConfirmationModal(false)}
                heading={isRegistered? 'Unregister Prep Confirmation' : 'Register Prep Confirmation'}
                onConfirm={() => {
                    if (isRegistered) {
                        onClickUnregisterPrep();
                    }
                    else {
                        onClickRegisterPrep();

                    }
                }} >
                {                 
                        <>
                            <div>Are you sure you want to {isRegistered ? 'unregister from' : 'register to'} Prep List?</div>
                            {
                                !isRegistered &&
                                <div style = {{color: 'red'}}>If you miss voting on voting period you should pay penalty to re-register.</div>

                            }
                        </> 
                }

            </ConfirmationModal>

            <UserInfoFormModal
                show={modalShow}
                setModalShow = {setModalShow}
                onHide={() => setModalShow(false)}
      />
        </Row>
    )
}

const mapStateToProps = state => ({
    address: state.account.address,
    isPrep: state.account.isPrep,
    isRegistered: state.account.isRegistered,
    payPenalty: state.account.payPenalty,

    period: state.period.period,
    firstName: state.user.firstName,
    lastName: state.user.lastName

})

const mapDispatchToProps = dispatch => (
    {
        logout: () => dispatch(logout()),
        unregisterPrep: () => dispatch(unregisterPrep()),
        registerPrep: () => dispatch(registerPrep()),

    }
)

export default connect(mapStateToProps, mapDispatchToProps)(Header);