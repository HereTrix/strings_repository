import { FC } from "react"
import { Button, Container, Form, Row } from "react-bootstrap"
import { SubmitHandler, useForm } from "react-hook-form"
import Profile from "../model/Profile"
import { APIMethod, http } from "../Utils/network"

type Inputs = {
    email: string
    firstName: string
    lastName: string
}

type ProfileDetailsProps = {
    profile: Profile
}

const ProfileDetailsPage: FC<ProfileDetailsProps> = ({ profile }) => {

    const {
        register,
        handleSubmit,
        formState: { errors }
    } = useForm<Inputs>()

    const onSubmit: SubmitHandler<Inputs> = async (data) => {
        const result = await http<Profile>({
            method: APIMethod.post,
            path: "/api/profile",
            data: { "email": data.email, "first_name": data.firstName, "last_name": data.lastName }
        })

        if (result.error) {

        } else {

        }
    }

    return (
        <Container>
            <Form
                onSubmit={handleSubmit(onSubmit)}
                className="align-items-start">
                <Form.Group className="my-2">
                    <Form.Label>Email</Form.Label>
                    <Form.Control required
                        type="email"
                        placeholder="Email"
                        defaultValue={profile.email}
                        {...register("email")} />
                </Form.Group>
                <Form.Group className="my-2">
                    <Form.Label>First name</Form.Label>
                    <Form.Control required
                        type="text"
                        placeholder="First name"
                        defaultValue={profile.first_name}
                        {...register("firstName")} />
                </Form.Group>
                <Form.Group className="my-2">
                    <Form.Label>Last name</Form.Label>
                    <Form.Control required
                        type="text"
                        placeholder="Last name"
                        defaultValue={profile.last_name}
                        {...register("lastName")} />
                </Form.Group>
                <Form.Group className="my-2">
                    <Button
                        type="submit">
                        Save
                    </Button>
                </Form.Group>
            </Form>
        </Container>
    )
}

export default ProfileDetailsPage