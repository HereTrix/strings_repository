import { NavigateFunction, Location } from "react-router-dom";

interface HistoryNavigator {
    navigate: NavigateFunction,
    location: Location
}

export const history = {

} as HistoryNavigator