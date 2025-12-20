package model

type User struct {
    Name  string
    Email string
}

func (u *User) GetName() string {
    return u.Name
}

func (u *User) SetName(name string) {
    u.Name = name
}

