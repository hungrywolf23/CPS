import { call, put} from 'redux-saga/effects';
// import {
//   getCourseInfo,
// } from '../services/api';
import {fetchDraftsSuccess, fetchDraftsFailure} from '../../Reducers/proposalSlice';
import {PROPOSAL_ADD_URL} from '../../Constants';
import {getRequest} from '../helpers';

function* fetchDraftRequestWorker({payload}) {
  console.log("fetchDraftRequestWorker");
  try {
    const response = yield call(getRequest, {
      url: `redis/proposals?address=${payload.walletAddress}`,
      method: 'GET'
    });
    yield put(fetchDraftsSuccess(
      {
        response,
      }
    ));
  } catch (error) {
    yield put(fetchDraftsFailure());
  }
}


export default fetchDraftRequestWorker;